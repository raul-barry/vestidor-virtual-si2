from datetime import date, datetime, time, timezone
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.repositories.report_repository import ReportRepository
from app.models.organizacion import Organizacion
from app.schemas.report import (
    CategoryRankingResponse,
    CustomerReportResponse,
    DashboardReportResponse,
    InventoryReportResponse,
    ProductRankingResponse,
    RecentInventoryMovementResponse,
    SalesReportResponse,
)


class ReportService:
    def __init__(self, db: Session, organization_id: int) -> None:
        self.repository = ReportRepository(db, organization_id)

    def dashboard(self, id_usuario: int) -> DashboardReportResponse:
        users, clients, products, orders, sales, low_stock = self.repository.dashboard_counts()
        self._audit(id_usuario, "dashboard")
        return DashboardReportResponse(
            usuarios_totales=users,
            clientes_totales=clients,
            productos_totales=products,
            pedidos_totales=orders,
            ventas_totales=sales,
            productos_stock_bajo=low_stock,
        )

    def sales(
        self, id_usuario: int, fecha_inicio: date | None, fecha_fin: date | None,
        id_sucursal: int | None = None,
    ) -> SalesReportResponse:
        start, end = self._date_range(fecha_inicio, fecha_fin)
        if id_sucursal is not None and not self.repository.validate_branch(id_sucursal):
            from fastapi import HTTPException
            raise HTTPException(404, detail="Sucursal no encontrada")
        sales, orders, average = self.repository.sales_totals(start, end, id_sucursal)
        statuses = dict(self.repository.sales_by_status(start, end, id_sucursal))
        self._audit(id_usuario, "ventas")
        return SalesReportResponse(
            ventas_totales=sales,
            cantidad_pedidos=orders,
            promedio_compra=average,
            pedidos_por_estado=statuses,
        )

    def top_products(
        self, id_usuario: int, fecha_inicio: date | None = None,
        fecha_fin: date | None = None, id_sucursal: int | None = None,
    ) -> list[ProductRankingResponse]:
        start, end = self._date_range(fecha_inicio, fecha_fin)
        self._validate_branch(id_sucursal)
        report = [
            ProductRankingResponse(producto=name, cantidad_vendida=quantity, ingresos_generados=income)
            for name, quantity, income in self.repository.top_products(start, end, id_sucursal)
        ]
        self._audit(id_usuario, "productos más vendidos")
        return report

    def top_categories(
        self, id_usuario: int, fecha_inicio: date | None = None,
        fecha_fin: date | None = None, id_sucursal: int | None = None,
    ) -> list[CategoryRankingResponse]:
        start, end = self._date_range(fecha_inicio, fecha_fin)
        self._validate_branch(id_sucursal)
        report = [
            CategoryRankingResponse(categoria=name, cantidad_vendida=quantity, ventas_generadas=income)
            for name, quantity, income in self.repository.top_categories(start, end, id_sucursal)
        ]
        self._audit(id_usuario, "categorías más vendidas")
        return report

    def inventory(self, id_usuario: int, id_sucursal: int | None = None) -> InventoryReportResponse:
        self._validate_branch(id_sucursal)
        stock, low_stock, out_of_stock = self.repository.inventory_totals(id_sucursal)
        movements = [
            RecentInventoryMovementResponse(producto=product, tipo=movement_type, cantidad=quantity, fecha=movement_date)
            for product, movement_type, quantity, movement_date in self.repository.recent_inventory_movements(branch_id=id_sucursal)
        ]
        self._audit(id_usuario, "inventario")
        return InventoryReportResponse(
            stock_total=stock,
            productos_stock_bajo=low_stock,
            productos_sin_stock=out_of_stock,
            movimientos_recientes=movements,
        )

    def customers(self, id_usuario: int) -> CustomerReportResponse:
        month_start = datetime.combine(date.today().replace(day=1), time.min, tzinfo=timezone.utc)
        users, active_clients, new_clients, clients_with_orders = self.repository.customer_totals(month_start)
        self._audit(id_usuario, "clientes")
        return CustomerReportResponse(
            usuarios_registrados=users,
            clientes_activos=active_clients,
            clientes_nuevos_mes=new_clients,
            clientes_con_compras=clients_with_orders,
        )

    def branch_sales_comparison(
        self, id_usuario: int, organization: Organizacion, fecha_inicio: date | None,
        fecha_fin: date | None, branch_ids: list[int] | None = None,
        scoped_branch_id: int | None = None,
    ):
        from decimal import Decimal
        from fastapi import HTTPException
        from app.schemas.report import BranchSalesComparisonResponse, BranchSalesComparisonRow

        today = datetime.now(timezone(timedelta(hours=-4))).date()
        end = fecha_fin or today
        start = fecha_inicio or end - timedelta(days=29)
        start, end = self._date_range(start, end)
        if (end - start).days > 365:
            raise HTTPException(422, detail="El período no puede superar 366 días")
        requested = list(dict.fromkeys(branch_ids or []))
        if scoped_branch_id is not None:
            if requested and any(branch_id != scoped_branch_id for branch_id in requested):
                raise HTTPException(403, detail="Sucursal fuera del alcance asignado")
            requested = [scoped_branch_id]
        if requested and any(not self.repository.validate_branch(branch_id) for branch_id in requested):
            raise HTTPException(404, detail="Sucursal no encontrada")

        previous_end = start - timedelta(days=1)
        previous_start = previous_end - (end - start)
        raw = self.repository.branch_sales_comparison(start, end, requested or None)
        rows = []
        for branch_id, name, count, revenue, previous_count, previous_revenue in raw:
            revenue = Decimal(str(revenue or 0))
            previous_revenue = Decimal(str(previous_revenue or 0))
            count = int(count or 0)
            previous_count = int(previous_count or 0)
            variation = (
                ((revenue - previous_revenue) * Decimal("100") / abs(previous_revenue)).quantize(Decimal("0.01"))
                if previous_revenue != 0 else None
            )
            rows.append({
                "id_sucursal": branch_id, "sucursal": name, "cantidad_ventas": count,
                "ingresos_netos": revenue, "ticket_promedio": revenue / count if count else Decimal("0"),
                "ventas_periodo_anterior": previous_count, "ingresos_periodo_anterior": previous_revenue,
                "variacion_porcentual": variation,
            })
        rows.sort(key=lambda row: (-row["ingresos_netos"], row["sucursal"].casefold()))
        for ranking, row in enumerate(rows, 1):
            row["ranking"] = ranking
        total_revenue = sum((row["ingresos_netos"] for row in rows), Decimal("0"))
        total_sales = sum(row["cantidad_ventas"] for row in rows)
        previous_total = sum((row["ingresos_periodo_anterior"] for row in rows), Decimal("0"))
        total_variation = (
            ((total_revenue - previous_total) * Decimal("100") / abs(previous_total)).quantize(Decimal("0.01"))
            if previous_total != 0 else None
        )
        def top_id(key: str, *, reverse: bool = True):
            if not rows:
                return None
            if reverse and not any(row[key] > 0 for row in rows):
                return None
            return sorted(rows, key=lambda row: ((-row[key] if reverse else row[key]), row["sucursal"].casefold()))[0]["id_sucursal"]

        self._audit(id_usuario, "comparación de ventas por sucursal")
        return BranchSalesComparisonResponse(
            organizacion=organization.nombre,
            periodo={"desde": start, "hasta": end},
            periodo_anterior={"desde": previous_start, "hasta": previous_end},
            sucursales=[BranchSalesComparisonRow(**row) for row in rows],
            totales={
                "ingresos_netos": total_revenue, "cantidad_ventas": total_sales,
                "ticket_promedio": total_revenue / total_sales if total_sales else Decimal("0"),
                "variacion_porcentual": total_variation,
            },
            destacados={
                "mayores_ingresos": top_id("ingresos_netos"),
                "mas_transacciones": top_id("cantidad_ventas"),
                "mayor_ticket_promedio": top_id("ticket_promedio"),
                "menores_ingresos": top_id("ingresos_netos", reverse=False),
            },
            zona_horaria="UTC-04:00",
        )

    @staticmethod
    def _date_range(fecha_inicio: date | None, fecha_fin: date | None) -> tuple[date | None, date | None]:
        if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
            raise AppException("fecha_inicio no puede ser posterior a fecha_fin", status_code=422)
        return fecha_inicio, fecha_fin

    def _audit(self, id_usuario: int, report_name: str) -> None:
        self.repository.create_audit(id_usuario, report_name)
        self.repository.db.commit()

    def _validate_branch(self, id_sucursal: int | None) -> None:
        if id_sucursal is not None and not self.repository.validate_branch(id_sucursal):
            from fastapi import HTTPException
            raise HTTPException(404, detail="Sucursal no encontrada")
