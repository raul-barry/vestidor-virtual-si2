from datetime import date, datetime, time, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.repositories.report_repository import ReportRepository
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
