"""Tenant-scoped demand forecasting and deterministic customer clustering."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from math import floor, sqrt
from statistics import fmean
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.repositories.report_repository import ReportRepository


MODEL_VERSION = "weekly-seasonal-trend-v1"
MIN_HISTORY_DAYS = 42
FORECAST_DAYS = 7
MAX_PERIOD_DAYS = 366


class PredictiveAnalyticsService:
    def __init__(self, db: Session) -> None:
        organization_id = db.info.get("organization_id")
        if not isinstance(organization_id, int):
            raise HTTPException(403, detail="Falta el contexto de la organización autenticada.")
        self.db = db
        self.organization_id = organization_id
        self.repository = ReportRepository(db, organization_id)

    @staticmethod
    def _date(value: Any) -> date:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return date.fromisoformat(str(value)[:10])

    @staticmethod
    def _period(start: date | None, end: date | None) -> tuple[date, date]:
        end = end or date.today()
        start = start or end - timedelta(days=179)
        if start > end:
            raise HTTPException(422, detail="La fecha inicial no puede ser posterior a la final.")
        if (end - start).days + 1 > MAX_PERIOD_DAYS:
            raise HTTPException(422, detail=f"El período máximo es de {MAX_PERIOD_DAYS} días.")
        return start, end

    @staticmethod
    def _linear_slope(values: list[float]) -> float:
        if len(values) < 2:
            return 0.0
        x = list(range(len(values)))
        x_mean = fmean(x)
        y_mean = fmean(values)
        denominator = sum((value - x_mean) ** 2 for value in x)
        if denominator == 0:
            return 0.0
        return sum((x_value - x_mean) * (y_value - y_mean)
                   for x_value, y_value in zip(x, values)) / denominator

    @classmethod
    def _seasonal_value(cls, values: list[float], target_index: int) -> float:
        same_weekday = [
            values[target_index - 7 * step]
            for step in range(1, 5)
            if target_index - 7 * step >= 0
        ]
        if same_weekday:
            return fmean(same_weekday)
        return fmean(values[-min(len(values), 7):]) if values else 0.0

    @classmethod
    def _evaluate(cls, values: list[float]) -> dict[str, float | None]:
        if len(values) < MIN_HISTORY_DAYS:
            return {"mae": None, "wape_porcentaje": None}
        split = len(values) - FORECAST_DAYS
        actual = values[split:]
        predicted = [max(0.0, cls._seasonal_value(values[:index], index))
                     for index in range(split, len(values))]
        absolute_errors = [abs(a - p) for a, p in zip(actual, predicted)]
        mae = sum(absolute_errors) / len(absolute_errors)
        actual_total = sum(actual)
        wape = (sum(absolute_errors) * 100 / actual_total) if actual_total else None
        return {
            "mae": round(mae, 3),
            "wape_porcentaje": round(wape, 2) if wape is not None else None,
        }

    @classmethod
    def _forecast(cls, values: list[float]) -> tuple[list[float], float]:
        recent = values[-28:]
        slope = cls._linear_slope(recent)
        forecast: list[float] = []
        for offset in range(FORECAST_DAYS):
            seasonal = cls._seasonal_value(values, len(values) + offset)
            # Damp the fitted trend to keep short-term forecasts conservative.
            forecast.append(round(max(0.0, seasonal + slope * (offset + 1) * 0.35), 2))
        return forecast, slope

    def _series(
        self, start: date, end: date, branch_id: int | None, product_id: int | None,
    ) -> tuple[dict[tuple[int, int], dict], dict[tuple[int, int], dict]]:
        if branch_id is not None and not self.repository.validate_branch(branch_id):
            raise HTTPException(404, detail="Sucursal no encontrada.")
        if product_id is not None and not self.repository.validate_product(product_id):
            raise HTTPException(404, detail="Producto no encontrado.")
        sales: dict[tuple[int, int], dict] = {}
        for sale_date, pid, product_name, bid, branch_name, quantity in (
            self.repository.predictive_daily_product_sales(start, end, branch_id, product_id)
        ):
            key = (int(pid), int(bid))
            row = sales.setdefault(key, {
                "producto_id": int(pid), "producto": product_name,
                "sucursal_id": int(bid), "sucursal": branch_name, "ventas": {},
            })
            row["ventas"][self._date(sale_date)] = float(quantity or 0)
        inventory: dict[tuple[int, int], dict] = {}
        for pid, product_name, bid, branch_name, stock in (
            self.repository.predictive_inventory_by_product_branch(branch_id, product_id)
        ):
            key = (int(pid), int(bid))
            inventory[key] = {
                "producto_id": int(pid), "producto": product_name,
                "sucursal_id": int(bid), "sucursal": branch_name,
                "stock_disponible": int(stock or 0),
            }
        return sales, inventory

    def dashboard(
        self, start: date | None = None, end: date | None = None,
        branch_id: int | None = None, product_id: int | None = None,
    ) -> dict:
        start, end = self._period(start, end)
        sales, inventory = self._series(start, end, branch_id, product_id)
        keys = sorted(set(sales) | set(inventory))
        predictions = []
        all_errors: list[float] = []
        all_actual: list[float] = []
        weekly_actual: dict[date, float] = defaultdict(float)
        calendar = [start + timedelta(days=offset)
                    for offset in range((end - start).days + 1)]

        for key in keys:
            sales_row = sales.get(key, {})
            stock_row = inventory.get(key, {})
            values = [sales_row.get("ventas", {}).get(day, 0.0) for day in calendar]
            if values:
                for day, quantity in zip(calendar, values):
                    monday = day - timedelta(days=day.weekday())
                    weekly_actual[monday] += quantity
            known_sales_days = sum(quantity > 0 for quantity in values)
            enough = len(values) >= MIN_HISTORY_DAYS and known_sales_days >= 6
            item = {
                "producto_id": key[0],
                "producto": sales_row.get("producto", stock_row.get("producto", "")),
                "sucursal_id": key[1],
                "sucursal": sales_row.get("sucursal", stock_row.get("sucursal", "Sin sucursal")),
                "periodo_historico": {"desde": start, "hasta": end},
                "dias_historicos": len(values),
                "dias_con_ventas": known_sales_days,
                "stock_disponible": stock_row.get("stock_disponible"),
                "estado_modelo": "evaluado" if enough else "datos_insuficientes",
                "prediccion_7_dias": None,
                "tendencia": "sin datos",
                "riesgo_inventario": "no_evaluable",
                "evaluacion": {"mae": None, "wape_porcentaje": None},
            }
            if enough:
                evaluation = self._evaluate(values)
                forecast, slope = self._forecast(values)
                expected = round(sum(forecast), 2)
                stock = stock_row.get("stock_disponible")
                if stock is None:
                    risk = "inventario_no_registrado"
                elif expected > stock:
                    risk = "posible_agotamiento"
                elif expected > 0 and stock >= expected * 8:
                    risk = "posible_exceso"
                else:
                    risk = "estable"
                item.update({
                    "prediccion_7_dias": {
                        "demanda_esperada": expected,
                        "demanda_diaria": forecast,
                        "desde": end + timedelta(days=1),
                        "hasta": end + timedelta(days=FORECAST_DAYS),
                    },
                    "tendencia": "creciente" if slope > 0.1 else "decreciente" if slope < -0.1 else "estable",
                    "riesgo_inventario": risk,
                    "evaluacion": evaluation,
                })
                if evaluation["mae"] is not None:
                    all_errors.extend(abs(values[-FORECAST_DAYS + index] - predicted)
                                      for index, predicted in enumerate(
                                          [max(0.0, self._seasonal_value(values[:-FORECAST_DAYS + index],
                                                                        len(values) - FORECAST_DAYS + index))
                                           for index in range(FORECAST_DAYS)]
                                      ))
                    all_actual.extend(values[-FORECAST_DAYS:])
            predictions.append(item)

        total_actual = sum(all_actual)
        overall_evaluation = {
            "productos_evaluados": sum(item["estado_modelo"] == "evaluado" for item in predictions),
            "mae_unidades": round(sum(all_errors) / len(all_errors), 3) if all_errors else None,
            "wape_porcentaje": round(sum(all_errors) * 100 / total_actual, 2) if total_actual else None,
            "metodo": "validacion temporal de una semana contra promedio estacional por dia de semana",
        }
        weekly_trend = [
            {"semana_desde": week, "unidades_vendidas": round(units, 2)}
            for week, units in sorted(weekly_actual.items())[-12:]
        ]
        return {
            "periodo": {"desde": start, "hasta": end},
            "modelo": {
                "version": MODEL_VERSION,
                "actualizado_en": datetime.now(timezone.utc),
                "metodo": "promedio estacional semanal con tendencia lineal amortiguada",
                "minimo_dias_historicos": MIN_HISTORY_DAYS,
            },
            "evaluacion": overall_evaluation,
            "tendencia_historica_semanal": weekly_trend,
            "predicciones": predictions,
            "productos_con_datos_insuficientes": sum(
                item["estado_modelo"] == "datos_insuficientes" for item in predictions
            ),
        }

    def history(
        self, start: date, end: date, branch_id: int | None = None,
        product_id: int | None = None,
    ) -> dict:
        start, end = self._period(start, end)
        history_start = start - timedelta(days=28)
        sales, _ = self._series(history_start, end, branch_id, product_id)
        results = []
        window_start = start
        while window_start + timedelta(days=6) <= end:
            window_end = window_start + timedelta(days=6)
            for row in sales.values():
                all_days = [history_start + timedelta(days=i)
                            for i in range((end - history_start).days + 1)]
                values = [row["ventas"].get(day, 0.0) for day in all_days]
                offset = (window_start - history_start).days
                if offset < 28:
                    continue
                forecast = [round(max(0.0, self._seasonal_value(values[:offset + i], offset + i)), 2)
                            for i in range(7)]
                actual = [values[offset + i] for i in range(7)]
                results.append({
                    "producto_id": row["producto_id"],
                    "producto": row["producto"],
                    "sucursal_id": row["sucursal_id"],
                    "sucursal": row["sucursal"],
                    "periodo": {"desde": window_start, "hasta": window_end},
                    "demanda_predicha": round(sum(forecast), 2),
                    "demanda_real": round(sum(actual), 2),
                    "error_absoluto": round(abs(sum(actual) - sum(forecast)), 2),
                    "tipo_resultado": "backtest_reconstruido",
                })
            window_start += timedelta(days=7)
        results.sort(key=lambda item: (item["periodo"]["desde"], item["producto"]))
        return {
            "periodo_evaluado": {"desde": start, "hasta": end},
            "nota": "Backtest reconstruido con datos disponibles; no representa predicciones persistidas en su fecha.",
            "resultados": results[:500],
        }

    @staticmethod
    def _distance(left: list[float], right: list[float]) -> float:
        return sqrt(sum((a - b) ** 2 for a, b in zip(left, right)))

    @classmethod
    def _kmeans(cls, points: list[list[float]], k: int) -> tuple[list[int], list[list[float]]]:
        means = [fmean(point[column] for point in points) for column in range(len(points[0]))]
        centers = [max(points, key=lambda point: cls._distance(point, means))[:]]
        while len(centers) < k:
            candidate = max(points, key=lambda point: min(cls._distance(point, center) for center in centers))
            if all(cls._distance(candidate, center) > 1e-9 for center in centers):
                centers.append(candidate[:])
            else:
                centers.append(points[len(centers) % len(points)][:])
        labels: list[int] = []
        for _ in range(50):
            labels = [min(range(k), key=lambda index: cls._distance(point, centers[index]))
                      for point in points]
            updated = []
            for cluster in range(k):
                members = [point for point, label in zip(points, labels) if label == cluster]
                updated.append(
                    [fmean(point[column] for point in members) for column in range(len(points[0]))]
                    if members else centers[cluster]
                )
            if all(cls._distance(old, new) < 1e-6 for old, new in zip(centers, updated)):
                centers = updated
                break
            centers = updated
        labels = [min(range(k), key=lambda index: cls._distance(point, centers[index]))
                  for point in points]
        return labels, centers

    @classmethod
    def _davies_bouldin(cls, points: list[list[float]], labels: list[int],
                        centers: list[list[float]]) -> float:
        k = len(centers)
        scatter = []
        for cluster in range(k):
            members = [point for point, label in zip(points, labels) if label == cluster]
            if not members:
                return float("inf")
            scatter.append(fmean(cls._distance(point, centers[cluster]) for point in members))
        ratios = []
        for cluster in range(k):
            ratios.append(max(
                (scatter[cluster] + scatter[other]) /
                max(cls._distance(centers[cluster], centers[other]), 1e-9)
                for other in range(k) if other != cluster
            ))
        return fmean(ratios)

    def segments(self, as_of: date | None = None, branch_id: int | None = None) -> dict:
        as_of = as_of or date.today()
        if branch_id is not None and not self.repository.validate_branch(branch_id):
            raise HTTPException(404, detail="Sucursal no encontrada.")
        features = self.repository.predictive_customer_purchase_features(as_of, branch_id)
        if len(features) < 6:
            return {
                "estado": "datos_insuficientes",
                "clientes_analizados": len(features),
                "minimo_clientes": 6,
                "variables": ["compras_pagadas", "gasto_pagado", "dias_desde_ultima_compra"],
                "segmentos": [],
                "actualizado_en": datetime.now(timezone.utc),
            }
        raw = []
        for _, order_count, spend, last_order in features:
            recency = (as_of - self._date(last_order)).days if last_order else 366
            raw.append([float(order_count), float(spend or 0), float(recency)])
        means = [fmean(point[column] for point in raw) for column in range(3)]
        deviations = []
        for column in range(3):
            variance = fmean((point[column] - means[column]) ** 2 for point in raw)
            deviations.append(sqrt(variance) or 1.0)
        normalized = [[(point[column] - means[column]) / deviations[column]
                       for column in range(3)] for point in raw]
        maximum_k = min(5, max(2, floor(sqrt(len(raw) / 2))), len(raw) - 1)
        candidates = []
        for k in range(2, maximum_k + 1):
            labels, centers = self._kmeans(normalized, k)
            score = self._davies_bouldin(normalized, labels, centers)
            candidates.append((score, k, labels))
        score, chosen_k, labels = min(candidates, key=lambda candidate: (candidate[0], candidate[1]))
        segments = []
        for cluster in range(chosen_k):
            members = [raw[index] for index, label in enumerate(labels) if label == cluster]
            avg_orders = fmean(point[0] for point in members)
            avg_spend = fmean(point[1] for point in members)
            avg_recency = fmean(point[2] for point in members)
            activity = "alta actividad" if avg_orders >= means[0] else "actividad moderada o baja"
            value = "gasto alto" if avg_spend >= means[1] else "gasto moderado o bajo"
            recency_label = "compra reciente" if avg_recency < means[2] else "recencia elevada"
            segments.append({
                "segmento": cluster + 1,
                "clientes": len(members),
                "caracteristicas": [activity, value, recency_label],
                "promedios": {
                    "compras_pagadas": round(avg_orders, 2),
                    "gasto_pagado": round(avg_spend, 2),
                    "dias_desde_ultima_compra": round(avg_recency, 1),
                },
            })
        return {
            "estado": "calculado",
            "clientes_analizados": len(features),
            "fecha_corte": as_of,
            "variables": ["compras_pagadas", "gasto_pagado", "dias_desde_ultima_compra"],
            "normalizacion": "z-score",
            "algoritmo": "K-Means determinista; k elegido por indice Davies-Bouldin",
            "k": chosen_k,
            "indice_davies_bouldin": round(score, 4),
            "segmentos": segments,
            "actualizado_en": datetime.now(timezone.utc),
        }
