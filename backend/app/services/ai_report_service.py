"""Tenant-scoped report metrics with optional Groq qualitative analysis."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
import json
import re

from sqlalchemy.orm import Session

from app.models.usuario import Usuario
from app.repositories.report_repository import ReportRepository
from app.schemas.report import AiReportRequest, AiReportResponse
from app.services.audit_service import AuditService
from app.services.ai_provider_service import AIProviderError, AIProviderService


class AiReportService:
    def __init__(self, db: Session, client: AIProviderService | None = None) -> None:
        organization_id = db.info.get("organization_id")
        if not isinstance(organization_id, int):
            raise ValueError("Falta el contexto de la organización autenticada.")
        self.db = db
        self.organization_id = organization_id
        self.repository = ReportRepository(db, organization_id)
        self.client = client or AIProviderService(db)

    @staticmethod
    def _money(value: Decimal) -> str:
        return str(value.quantize(Decimal("0.01")))

    def _metrics(self, request: AiReportRequest, start: date, end: date) -> dict:
        branch_id = request.id_sucursal
        if branch_id is not None and not self.repository.validate_branch(branch_id):
            from fastapi import HTTPException
            raise HTTPException(404, detail="Sucursal no encontrada")

        if request.tipo == "ventas":
            amount, orders, average = self.repository.sales_totals(start, end, branch_id)
            return {
                "ventas_pagadas": self._money(amount),
                "pedidos_pagados": orders,
                "promedio_pago": self._money(average),
                "pedidos_por_estado": dict(self.repository.sales_by_status(start, end, branch_id)),
            }
        if request.tipo == "productos":
            return {
                "productos_mas_vendidos": [
                    {"producto": name, "unidades": quantity, "ingresos": self._money(income)}
                    for name, quantity, income in self.repository.top_products(start, end, branch_id)
                ],
                "categorias_mas_vendidas": [
                    {"categoria": name, "unidades": quantity, "ingresos": self._money(income)}
                    for name, quantity, income in self.repository.top_categories(start, end, branch_id)
                ],
            }
        if request.tipo == "sucursales":
            return {
                "rendimiento_por_sucursal": [
                    {"id_sucursal": branch, "sucursal": name,
                     "pedidos_pagados": orders, "ventas_pagadas": self._money(amount)}
                    for branch, name, orders, amount
                    in self.repository.branch_performance(start, end, branch_id)
                ]
            }
        if request.tipo == "inventario":
            stock, low_stock, empty = self.repository.inventory_totals(branch_id)
            reservation_count, reserved_units = self.repository.reservation_totals(start, end, branch_id)
            return {
                "stock_disponible_total": stock,
                "registros_stock_bajo": low_stock,
                "registros_sin_stock": empty,
                "reservas_vigentes": reservation_count,
                "unidades_reservadas": reserved_units,
            }

        length = (end - start).days + 1
        previous_end = start - timedelta(days=1)
        previous_start = previous_end - timedelta(days=length - 1)
        current_sales, current_orders, _ = self.repository.sales_totals(start, end, branch_id)
        previous_sales, previous_orders, _ = self.repository.sales_totals(
            previous_start, previous_end, branch_id
        )
        change = None
        if previous_sales != 0:
            change = self._money((current_sales - previous_sales) * Decimal("100") / previous_sales)
        return {
            "periodo_actual": {
                "ventas_pagadas": self._money(current_sales),
                "pedidos_pagados": current_orders,
            },
            "periodo_anterior": {
                "desde": previous_start.isoformat(),
                "hasta": previous_end.isoformat(),
                "ventas_pagadas": self._money(previous_sales),
                "pedidos_pagados": previous_orders,
            },
            "variacion_ventas_porcentaje_calculada": change,
        }

    @staticmethod
    def _extract_analysis(payload: dict) -> tuple[list[str], list[str]]:
        try:
            parts = payload["candidates"][0]["content"]["parts"]
            text = next(
                part["text"] for part in parts
                if isinstance(part, dict) and isinstance(part.get("text"), str)
            )
            result = json.loads(text)
            observations = result["observaciones"]
            recommendations = result["recomendaciones"]
        except (KeyError, IndexError, StopIteration, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise AIProviderError("El proveedor de IA devolvió un análisis no estructurado.") from exc
        if not isinstance(observations, list) or not isinstance(recommendations, list):
            raise AIProviderError("El proveedor de IA devolvió un análisis no estructurado.")
        return (
            [item.strip()[:500] for item in observations[:8] if isinstance(item, str) and item.strip()],
            [item.strip()[:500] for item in recommendations[:8] if isinstance(item, str) and item.strip()],
        )

    def generate(self, user: Usuario, request: AiReportRequest) -> AiReportResponse:
        start, end, metrics = self.calculate(request)
        safe_question = re.sub(
            r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", "[dato personal omitido]",
            request.consulta, flags=re.IGNORECASE,
        )
        facts = {"tipo": request.tipo, "desde": start.isoformat(), "hasta": end.isoformat(), "metricas": metrics}
        prompt = (
            "Analiza los datos agregados reales de la organización autenticada. Los datos incluidos son la única fuente factual. "
            "No inventes cantidades, montos, porcentajes, fechas, productos ni sucursales; no recalcules ni "
            "modifiques las métricas. Si faltan datos, dilo claramente. Separa observaciones descriptivas de "
            "recomendaciones cualitativas; no presentes recomendaciones como hechos ni pidas datos personales. "
            "Devuelve solo JSON con las claves observaciones y recomendaciones, ambas listas de cadenas en español.\n"
            f"Consulta: {safe_question or 'Resume los hallazgos y propone acciones prudentes.'}\n"
            f"Datos calculados por el servidor: {json.dumps(facts, ensure_ascii=False, separators=(',', ':'))}"
        )
        audit_details = {
            "tipo": request.tipo,
            "canal": request.canal,
            "desde": start.isoformat(),
            "hasta": end.isoformat(),
            "id_sucursal": request.id_sucursal,
        }
        try:
            payload = self.client.generate_content({
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "responseSchema": {
                        "type": "OBJECT",
                        "properties": {
                            "observaciones": {"type": "ARRAY", "items": {"type": "STRING"}},
                            "recomendaciones": {"type": "ARRAY", "items": {"type": "STRING"}},
                        },
                        "required": ["observaciones", "recomendaciones"],
                    },
                },
            }, capability="business_reports")
            observations, recommendations = self._extract_analysis(payload)
        except AIProviderError:
            AuditService.record(
                self.db, organization_id=self.organization_id, actor_id=user.id_usuario,
                actor_role=user.rol.nombre, action="REPORTE_IA_CONSULTADO",
                entity="Reporte", entity_id=request.tipo, result="ERROR",
                details=audit_details,
            )
            self.db.commit()
            raise
        AuditService.record(
            self.db, organization_id=self.organization_id, actor_id=user.id_usuario,
            actor_role=user.rol.nombre, action="REPORTE_IA_CONSULTADO",
            entity="Reporte", entity_id=request.tipo, details=audit_details,
        )
        self.db.commit()
        return AiReportResponse(
            tipo=request.tipo,
            periodo={"desde": start, "hasta": end},
            metricas_calculadas=metrics,
            observaciones_ia=observations,
            recomendaciones_ia=recommendations,
        )

    def calculate(self, request: AiReportRequest) -> tuple[date, date, dict]:
        """Return authoritative report metrics for exports without duplicating CU30 calculations."""
        end = request.fecha_fin or date.today()
        start = request.fecha_inicio or end - timedelta(days=29)
        return start, end, self._metrics(request, start, end)
