from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.bitacora import Bitacora
from app.models.categoria import Categoria
from app.models.cliente import Cliente
from app.models.inventario import Inventario
from app.models.movimiento_inventario import MovimientoInventario
from app.models.pago import Pago
from app.models.pedido import Pedido
from app.models.pedido_detalle import PedidoDetalle
from app.models.producto import Producto
from app.models.producto_variante import ProductoVariante
from app.models.usuario import Usuario


class ReportRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def dashboard_counts(self) -> tuple[int, int, int, int, Decimal, int]:
        users = self.db.scalar(select(func.count(Usuario.id_usuario))) or 0
        clients = self.db.scalar(select(func.count(Cliente.id_cliente))) or 0
        products = self.db.scalar(select(func.count(Producto.id_producto))) or 0
        orders = self.db.scalar(select(func.count(Pedido.id_pedido))) or 0
        sales = self.db.scalar(
            select(func.coalesce(func.sum(Pago.monto), Decimal("0"))).where(Pago.estado == "APROBADO")
        ) or Decimal("0")
        low_stock = self.db.scalar(
            select(func.count(Inventario.id_inventario)).where(Inventario.stock_disponible < 5)
        ) or 0
        return users, clients, products, orders, sales, low_stock

    def sales_totals(self, start: date | None, end: date | None) -> tuple[Decimal, int, Decimal]:
        statement = select(
            func.coalesce(func.sum(Pago.monto), Decimal("0")),
            func.count(Pedido.id_pedido),
            func.coalesce(func.avg(Pago.monto), Decimal("0")),
        ).join(Pedido, Pago.id_pedido == Pedido.id_pedido).where(Pago.estado == "APROBADO")
        if start is not None:
            statement = statement.where(func.date(Pedido.fecha_pedido) >= start)
        if end is not None:
            statement = statement.where(func.date(Pedido.fecha_pedido) <= end)
        sales, orders, average = self.db.execute(statement).one()
        return sales or Decimal("0"), orders or 0, average or Decimal("0")

    def sales_by_status(self, start: date | None, end: date | None) -> list[tuple[str, int]]:
        statement = (
            select(Pedido.estado, func.count(Pedido.id_pedido))
            .join(Pago, Pago.id_pedido == Pedido.id_pedido)
            .where(Pago.estado == "APROBADO")
            .group_by(Pedido.estado)
        )
        if start is not None:
            statement = statement.where(func.date(Pedido.fecha_pedido) >= start)
        if end is not None:
            statement = statement.where(func.date(Pedido.fecha_pedido) <= end)
        return [(estado, count) for estado, count in self.db.execute(statement).all()]

    def top_products(self) -> list[tuple[str, int, Decimal]]:
        statement = (
            select(
                Producto.nombre,
                func.sum(PedidoDetalle.cantidad),
                func.sum(PedidoDetalle.cantidad * PedidoDetalle.precio_unitario),
            )
            .select_from(PedidoDetalle)
            .join(Pedido, PedidoDetalle.id_pedido == Pedido.id_pedido)
            .join(Pago, Pago.id_pedido == Pedido.id_pedido)
            .join(ProductoVariante, PedidoDetalle.id_variante == ProductoVariante.id_variante)
            .join(Producto, ProductoVariante.id_producto == Producto.id_producto)
            .where(Pago.estado == "APROBADO")
            .group_by(Producto.id_producto, Producto.nombre)
            .order_by(func.sum(PedidoDetalle.cantidad).desc())
        )
        return [(name, quantity, income) for name, quantity, income in self.db.execute(statement).all()]

    def top_categories(self) -> list[tuple[str, int, Decimal]]:
        statement = (
            select(
                Categoria.nombre,
                func.sum(PedidoDetalle.cantidad),
                func.sum(PedidoDetalle.cantidad * PedidoDetalle.precio_unitario),
            )
            .select_from(PedidoDetalle)
            .join(Pedido, PedidoDetalle.id_pedido == Pedido.id_pedido)
            .join(Pago, Pago.id_pedido == Pedido.id_pedido)
            .join(ProductoVariante, PedidoDetalle.id_variante == ProductoVariante.id_variante)
            .join(Producto, ProductoVariante.id_producto == Producto.id_producto)
            .join(Categoria, Producto.id_categoria == Categoria.id_categoria)
            .where(Pago.estado == "APROBADO")
            .group_by(Categoria.id_categoria, Categoria.nombre)
            .order_by(func.sum(PedidoDetalle.cantidad).desc())
        )
        return [(name, quantity, income) for name, quantity, income in self.db.execute(statement).all()]

    def inventory_totals(self) -> tuple[int, int, int]:
        statement = select(
            func.coalesce(func.sum(Inventario.stock_disponible), 0),
            func.coalesce(func.sum(case((Inventario.stock_disponible < 5, 1), else_=0)), 0),
            func.coalesce(func.sum(case((Inventario.stock_disponible == 0, 1), else_=0)), 0),
        )
        return tuple(self.db.execute(statement).one())

    def recent_inventory_movements(self, limit: int = 10) -> list[tuple[str, str, int, datetime]]:
        statement = (
            select(
                Producto.nombre,
                MovimientoInventario.tipo_movimiento,
                MovimientoInventario.cantidad,
                MovimientoInventario.fecha_movimiento,
            )
            .select_from(MovimientoInventario)
            .join(Inventario, MovimientoInventario.id_inventario == Inventario.id_inventario)
            .join(ProductoVariante, Inventario.id_variante == ProductoVariante.id_variante)
            .join(Producto, ProductoVariante.id_producto == Producto.id_producto)
            .order_by(MovimientoInventario.fecha_movimiento.desc())
            .limit(limit)
        )
        return [tuple(row) for row in self.db.execute(statement).all()]

    def customer_totals(self, month_start: datetime) -> tuple[int, int, int, int]:
        users = self.db.scalar(select(func.count(Usuario.id_usuario))) or 0
        active_clients = self.db.scalar(
            select(func.count(Cliente.id_cliente))
            .join(Usuario, Cliente.id_usuario == Usuario.id_usuario)
            .where(func.upper(Usuario.estado) == "ACTIVO")
        ) or 0
        new_clients = self.db.scalar(
            select(func.count(Cliente.id_cliente)).where(Cliente.fecha_registro >= month_start)
        ) or 0
        clients_with_orders = self.db.scalar(select(func.count(func.distinct(Pedido.id_cliente)))) or 0
        return users, active_clients, new_clients, clients_with_orders

    def create_audit(self, id_usuario: int, report_name: str) -> Bitacora:
        audit = Bitacora(id_usuario=id_usuario, accion=f"Consulta reporte administrativo: {report_name}")
        self.db.add(audit)
        self.db.flush()
        self.db.refresh(audit)
        return audit
