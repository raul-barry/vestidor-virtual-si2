from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import and_, case, distinct, exists, func, or_, select
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
from app.models.reserva import Reserva
from app.models.sucursal import Sucursal
from app.models.usuario import Usuario


class ReportRepository:
    """Read report data only from the authenticated organization's records."""

    def __init__(self, db: Session, organization_id: int) -> None:
        context_organization = db.info.get("organization_id")
        if context_organization != organization_id:
            raise ValueError("El contexto del reporte no coincide con la organización autenticada.")
        self.db = db
        self.organization_id = organization_id

    def _organization_orders(self):
        organization_users = select(Usuario.id_usuario).where(
            Usuario.id_organizacion == self.organization_id
        )
        organization_clients = (
            select(Cliente.id_cliente)
            .join(Usuario, Cliente.id_usuario == Usuario.id_usuario)
            .where(Usuario.id_organizacion == self.organization_id)
        )
        organization_branches = select(Sucursal.id_sucursal).where(
            Sucursal.id_organizacion == self.organization_id
        )
        return or_(
            Pedido.id_vendedor.in_(organization_users),
            Pedido.id_cliente.in_(organization_clients),
            Pedido.id_sucursal_entrega.in_(organization_branches),
        )

    def _order_filters(
        self, start: date | None = None, end: date | None = None,
        branch_id: int | None = None,
    ) -> list:
        filters = [self._organization_orders()]
        business_zone = timezone(timedelta(hours=-4))  # Bolivia has a fixed UTC-04:00 offset.
        if start is not None:
            start_utc = datetime.combine(start, time.min, business_zone).astimezone(timezone.utc)
            filters.append(Pedido.fecha_pedido >= start_utc)
        if end is not None:
            end_exclusive = datetime.combine(end + timedelta(days=1), time.min, business_zone).astimezone(timezone.utc)
            filters.append(Pedido.fecha_pedido < end_exclusive)
        if branch_id is not None:
            filters.append(Pedido.id_sucursal_entrega == branch_id)
        return filters

    def validate_branch(self, branch_id: int) -> bool:
        return self.db.scalar(select(Sucursal.id_sucursal).where(
            Sucursal.id_sucursal == branch_id,
            Sucursal.id_organizacion == self.organization_id,
        )) is not None

    def validate_product(self, product_id: int) -> bool:
        return self.db.scalar(select(Producto.id_producto).where(
            Producto.id_producto == product_id,
            Producto.id_organizacion == self.organization_id,
        )) is not None

    def dashboard_counts(self) -> tuple[int, int, int, int, Decimal, int]:
        users = self.db.scalar(select(func.count(Usuario.id_usuario)).where(
            Usuario.id_organizacion == self.organization_id
        )) or 0
        clients = self.db.scalar(
            select(func.count(Cliente.id_cliente))
            .join(Usuario, Cliente.id_usuario == Usuario.id_usuario)
            .where(Usuario.id_organizacion == self.organization_id)
        ) or 0
        products = self.db.scalar(select(func.count(Producto.id_producto)).where(
            Producto.id_organizacion == self.organization_id
        )) or 0
        orders = self.db.scalar(select(func.count(Pedido.id_pedido)).where(
            *self._order_filters()
        )) or 0
        sales = self.db.scalar(
            select(func.coalesce(func.sum(Pago.monto), Decimal("0")))
            .join(Pedido, Pago.id_pedido == Pedido.id_pedido)
            .where(Pago.estado == "PAGADO", *self._order_filters())
        ) or Decimal("0")
        low_stock = self.db.scalar(
            select(func.count(Inventario.id_inventario))
            .join(Sucursal, Inventario.id_sucursal == Sucursal.id_sucursal)
            .where(Sucursal.id_organizacion == self.organization_id,
                   Inventario.stock_disponible < 5)
        ) or 0
        return users, clients, products, orders, sales, low_stock

    def sales_totals(
        self, start: date | None, end: date | None, branch_id: int | None = None,
    ) -> tuple[Decimal, int, Decimal]:
        statement = (
            select(
                func.coalesce(func.sum(Pago.monto), Decimal("0")),
                func.count(distinct(Pedido.id_pedido)),
                func.coalesce(func.avg(Pago.monto), Decimal("0")),
            )
            .join(Pedido, Pago.id_pedido == Pedido.id_pedido)
            .where(Pago.estado == "PAGADO", *self._order_filters(start, end, branch_id))
        )
        sales, orders, average = self.db.execute(statement).one()
        return sales or Decimal("0"), orders or 0, average or Decimal("0")

    def sales_by_status(
        self, start: date | None, end: date | None, branch_id: int | None = None,
    ) -> list[tuple[str, int]]:
        statement = (
            select(Pedido.estado, func.count(distinct(Pedido.id_pedido)))
            .join(Pago, Pago.id_pedido == Pedido.id_pedido)
            .where(Pago.estado == "PAGADO", *self._order_filters(start, end, branch_id))
            .group_by(Pedido.estado)
        )
        return [(estado, count) for estado, count in self.db.execute(statement).all()]

    def _paid_order_exists(self):
        return exists(select(Pago.id_pago).where(
            Pago.id_pedido == Pedido.id_pedido, Pago.estado == "PAGADO"
        ))

    def top_products(
        self, start: date | None = None, end: date | None = None,
        branch_id: int | None = None, limit: int = 10,
    ) -> list[tuple[str, int, Decimal]]:
        statement = (
            select(
                Producto.nombre,
                func.sum(PedidoDetalle.cantidad),
                func.sum(PedidoDetalle.cantidad * PedidoDetalle.precio_unitario),
            )
            .select_from(PedidoDetalle)
            .join(Pedido, PedidoDetalle.id_pedido == Pedido.id_pedido)
            .join(ProductoVariante, PedidoDetalle.id_variante == ProductoVariante.id_variante)
            .join(Producto, ProductoVariante.id_producto == Producto.id_producto)
            .where(
                Producto.id_organizacion == self.organization_id,
                self._paid_order_exists(),
                *self._order_filters(start, end, branch_id),
            )
            .group_by(Producto.id_producto, Producto.nombre)
            .order_by(func.sum(PedidoDetalle.cantidad).desc(), Producto.nombre)
            .limit(limit)
        )
        return [(name, quantity or 0, income or Decimal("0"))
                for name, quantity, income in self.db.execute(statement).all()]

    def top_categories(
        self, start: date | None = None, end: date | None = None,
        branch_id: int | None = None, limit: int = 10,
    ) -> list[tuple[str, int, Decimal]]:
        statement = (
            select(
                Categoria.nombre,
                func.sum(PedidoDetalle.cantidad),
                func.sum(PedidoDetalle.cantidad * PedidoDetalle.precio_unitario),
            )
            .select_from(PedidoDetalle)
            .join(Pedido, PedidoDetalle.id_pedido == Pedido.id_pedido)
            .join(ProductoVariante, PedidoDetalle.id_variante == ProductoVariante.id_variante)
            .join(Producto, ProductoVariante.id_producto == Producto.id_producto)
            .join(Categoria, Producto.id_categoria == Categoria.id_categoria)
            .where(
                Producto.id_organizacion == self.organization_id,
                self._paid_order_exists(),
                *self._order_filters(start, end, branch_id),
            )
            .group_by(Categoria.id_categoria, Categoria.nombre)
            .order_by(func.sum(PedidoDetalle.cantidad).desc(), Categoria.nombre)
            .limit(limit)
        )
        return [(name, quantity or 0, income or Decimal("0"))
                for name, quantity, income in self.db.execute(statement).all()]

    def inventory_totals(self, branch_id: int | None = None) -> tuple[int, int, int]:
        statement = (
            select(
                func.coalesce(func.sum(Inventario.stock_disponible), 0),
                func.coalesce(func.sum(case((Inventario.stock_disponible < 5, 1), else_=0)), 0),
                func.coalesce(func.sum(case((Inventario.stock_disponible == 0, 1), else_=0)), 0),
            )
            .join(Sucursal, Inventario.id_sucursal == Sucursal.id_sucursal)
            .where(Sucursal.id_organizacion == self.organization_id)
        )
        if branch_id is not None:
            statement = statement.where(Inventario.id_sucursal == branch_id)
        return tuple(self.db.execute(statement).one())

    def recent_inventory_movements(
        self, limit: int = 10, branch_id: int | None = None,
    ) -> list[tuple[str, str, int, datetime]]:
        statement = (
            select(
                Producto.nombre,
                MovimientoInventario.tipo_movimiento,
                MovimientoInventario.cantidad,
                MovimientoInventario.fecha_movimiento,
            )
            .select_from(MovimientoInventario)
            .join(Inventario, MovimientoInventario.id_inventario == Inventario.id_inventario)
            .join(Sucursal, Inventario.id_sucursal == Sucursal.id_sucursal)
            .join(ProductoVariante, Inventario.id_variante == ProductoVariante.id_variante)
            .join(Producto, ProductoVariante.id_producto == Producto.id_producto)
            .where(Sucursal.id_organizacion == self.organization_id,
                   Producto.id_organizacion == self.organization_id)
            .order_by(MovimientoInventario.fecha_movimiento.desc())
            .limit(limit)
        )
        if branch_id is not None:
            statement = statement.where(Sucursal.id_sucursal == branch_id)
        return [tuple(row) for row in self.db.execute(statement).all()]

    def reservation_totals(
        self, start: date | None = None, end: date | None = None,
        branch_id: int | None = None,
    ) -> tuple[int, int]:
        statement = (
            select(func.count(Reserva.id_reserva), func.coalesce(func.sum(Reserva.cantidad), 0))
            .join(Usuario, Reserva.id_usuario == Usuario.id_usuario)
            .join(Inventario, Reserva.id_inventario == Inventario.id_inventario)
            .join(Sucursal, Inventario.id_sucursal == Sucursal.id_sucursal)
            .where(
                Usuario.id_organizacion == self.organization_id,
                Sucursal.id_organizacion == self.organization_id,
                Reserva.estado.in_(("PENDIENTE", "CONFIRMADA", "ACTIVA")),
            )
        )
        if start is not None:
            statement = statement.where(func.date(Reserva.fecha) >= start)
        if end is not None:
            statement = statement.where(func.date(Reserva.fecha) <= end)
        if branch_id is not None:
            statement = statement.where(Inventario.id_sucursal == branch_id)
        count, quantity = self.db.execute(statement).one()
        return count or 0, quantity or 0

    def branch_performance(
        self, start: date | None, end: date | None, branch_id: int | None = None,
    ) -> list[tuple[int, str, int, Decimal]]:
        statement = (
            select(
                Sucursal.id_sucursal,
                Sucursal.nombre,
                func.count(distinct(Pedido.id_pedido)),
                func.coalesce(func.sum(Pago.monto), Decimal("0")),
            )
            .select_from(Sucursal)
            .outerjoin(Pedido, and_(
                Pedido.id_sucursal_entrega == Sucursal.id_sucursal,
                *self._order_filters(start, end, branch_id),
            ))
            .outerjoin(Pago, and_(Pago.id_pedido == Pedido.id_pedido, Pago.estado == "PAGADO"))
            .where(Sucursal.id_organizacion == self.organization_id)
            .group_by(Sucursal.id_sucursal, Sucursal.nombre)
            .order_by(func.coalesce(func.sum(Pago.monto), Decimal("0")).desc(), Sucursal.nombre)
        )
        if branch_id is not None:
            statement = statement.where(Sucursal.id_sucursal == branch_id)
        return [(id_branch, name, count or 0, total or Decimal("0"))
                for id_branch, name, count, total in self.db.execute(statement).all()]

    def predictive_daily_product_sales(
        self, start: date, end: date, branch_id: int | None = None,
        product_id: int | None = None,
    ) -> list[tuple]:
        statement = (
            select(
                func.date(Pedido.fecha_pedido),
                Producto.id_producto,
                Producto.nombre,
                func.coalesce(Pedido.id_sucursal_entrega, 0),
                func.coalesce(Sucursal.nombre, "Sin sucursal"),
                func.sum(PedidoDetalle.cantidad),
            )
            .select_from(PedidoDetalle)
            .join(Pedido, PedidoDetalle.id_pedido == Pedido.id_pedido)
            .join(ProductoVariante, PedidoDetalle.id_variante == ProductoVariante.id_variante)
            .join(Producto, ProductoVariante.id_producto == Producto.id_producto)
            .outerjoin(Sucursal, Pedido.id_sucursal_entrega == Sucursal.id_sucursal)
            .where(
                Producto.id_organizacion == self.organization_id,
                *self._order_filters(start, end, branch_id),
                self._paid_order_exists(),
                or_(Sucursal.id_organizacion == self.organization_id,
                    Pedido.id_sucursal_entrega.is_(None)),
            )
        )
        if product_id is not None:
            statement = statement.where(Producto.id_producto == product_id)
        statement = statement.group_by(
            func.date(Pedido.fecha_pedido), Producto.id_producto, Producto.nombre,
            Pedido.id_sucursal_entrega, Sucursal.nombre,
        ).order_by(func.date(Pedido.fecha_pedido))
        return [tuple(row) for row in self.db.execute(statement).all()]

    def predictive_inventory_by_product_branch(
        self, branch_id: int | None = None, product_id: int | None = None,
    ) -> list[tuple]:
        statement = (
            select(
                Producto.id_producto,
                Producto.nombre,
                Sucursal.id_sucursal,
                Sucursal.nombre,
                func.coalesce(func.sum(Inventario.stock_disponible), 0),
            )
            .select_from(Inventario)
            .join(Sucursal, Inventario.id_sucursal == Sucursal.id_sucursal)
            .join(ProductoVariante, Inventario.id_variante == ProductoVariante.id_variante)
            .join(Producto, ProductoVariante.id_producto == Producto.id_producto)
            .where(
                Sucursal.id_organizacion == self.organization_id,
                Producto.id_organizacion == self.organization_id,
            )
        )
        if branch_id is not None:
            statement = statement.where(Sucursal.id_sucursal == branch_id)
        if product_id is not None:
            statement = statement.where(Producto.id_producto == product_id)
        statement = statement.group_by(
            Producto.id_producto, Producto.nombre, Sucursal.id_sucursal, Sucursal.nombre,
        ).order_by(Producto.nombre, Sucursal.nombre)
        return [tuple(row) for row in self.db.execute(statement).all()]

    def predictive_customer_purchase_features(
        self, as_of: date, branch_id: int | None = None,
    ) -> list[tuple]:
        paid_orders = (
            select(
                Pedido.id_cliente.label("client_id"),
                func.count(distinct(Pedido.id_pedido)).label("orders"),
                func.coalesce(func.sum(Pago.monto), 0).label("spend"),
                func.max(Pedido.fecha_pedido).label("last_order"),
            )
            .join(Pago, Pago.id_pedido == Pedido.id_pedido)
            .where(
                Pago.estado == "PAGADO",
                Pedido.id_cliente.is_not(None),
                *self._order_filters(end=as_of, branch_id=branch_id),
            )
            .group_by(Pedido.id_cliente)
            .subquery()
        )
        statement = (
            select(
                Cliente.id_cliente,
                func.coalesce(paid_orders.c.orders, 0),
                func.coalesce(paid_orders.c.spend, 0),
                paid_orders.c.last_order,
            )
            .join(Usuario, Cliente.id_usuario == Usuario.id_usuario)
            .outerjoin(paid_orders, paid_orders.c.client_id == Cliente.id_cliente)
            .where(Usuario.id_organizacion == self.organization_id)
            .order_by(Cliente.id_cliente)
        )
        if branch_id is not None:
            statement = statement.where(paid_orders.c.client_id.is_not(None))
        return [tuple(row) for row in self.db.execute(statement).all()]

    def customer_totals(self, month_start: datetime) -> tuple[int, int, int, int]:
        users = self.db.scalar(select(func.count(Usuario.id_usuario)).where(
            Usuario.id_organizacion == self.organization_id
        )) or 0
        active_clients = self.db.scalar(
            select(func.count(Cliente.id_cliente))
            .join(Usuario, Cliente.id_usuario == Usuario.id_usuario)
            .where(Usuario.id_organizacion == self.organization_id,
                   func.upper(Usuario.estado) == "ACTIVO")
        ) or 0
        new_clients = self.db.scalar(
            select(func.count(Cliente.id_cliente))
            .join(Usuario, Cliente.id_usuario == Usuario.id_usuario)
            .where(Usuario.id_organizacion == self.organization_id,
                   Cliente.fecha_registro >= month_start)
        ) or 0
        clients_with_orders = self.db.scalar(
            select(func.count(distinct(Pedido.id_cliente))).where(
                Pedido.id_cliente.in_(select(Cliente.id_cliente).join(
                    Usuario, Cliente.id_usuario == Usuario.id_usuario
                ).where(Usuario.id_organizacion == self.organization_id)),
                self._organization_orders(),
            )
        ) or 0
        return users, active_clients, new_clients, clients_with_orders

    def create_audit(self, id_usuario: int, report_name: str) -> Bitacora:
        audit = Bitacora(id_usuario=id_usuario, accion=f"Consulta reporte administrativo: {report_name}")
        self.db.add(audit)
        self.db.flush()
        self.db.refresh(audit)
        return audit
