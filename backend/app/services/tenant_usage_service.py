from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql import exists

from app.core.exceptions import AppException
from app.models.inventario import Inventario
from app.models.organizacion import Organizacion
from app.models.pago import Pago
from app.models.pedido import Pedido
from app.models.pedido_detalle import PedidoDetalle
from app.models.producto import Producto
from app.models.producto_variante import ProductoVariante
from app.models.reserva import Reserva
from app.models.rol import Rol
from app.models.sucursal import Sucursal
from app.models.suscripcion import Suscripcion
from app.models.usuario import Usuario


class TenantUsageService:
    """Compute tenant-scoped usage using persisted operational records only."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_usage(
        self,
        organization_id: int,
        desde: date | None = None,
        hasta: date | None = None,
    ) -> dict:
        if desde is not None and hasta is not None and desde > hasta:
            raise AppException("La fecha desde no puede ser posterior a la fecha hasta", status_code=422)

        organization = self.db.get(Organizacion, organization_id)
        if organization is None:
            raise AppException("Organización no encontrada", status_code=404)

        start_at = datetime.combine(desde, time.min, tzinfo=timezone.utc) if desde else None
        end_at = datetime.combine(hasta + timedelta(days=1), time.min, tzinfo=timezone.utc) if hasta else None

        # This call also marks subscriptions past fecha_fin as VENCIDA using the
        # existing subscription rules. History provides the last contracted plan.
        from app.services.subscription_service import SubscriptionService

        subscriptions = SubscriptionService(self.db)
        subscriptions.current(organization_id)
        history = subscriptions.history(organization_id)
        latest = history[0] if history else None
        plan = latest.plan if latest is not None else None

        branch_count = self._scalar(
            select(func.count(Sucursal.id_sucursal)).where(
                Sucursal.id_organizacion == organization_id,
                func.upper(Sucursal.estado) == "ACTIVA",
            )
        )
        active_users = self._scalar(
            select(func.count(Usuario.id_usuario))
            .join(Rol, Rol.id_rol == Usuario.id_rol)
            .where(
                Usuario.id_organizacion == organization_id,
                Rol.nombre != "ADMINISTRADOR_PLATAFORMA",
                func.upper(Usuario.estado) == "ACTIVO",
            )
        )
        product_count = self._scalar(
            select(func.count(Producto.id_producto)).where(Producto.id_organizacion == organization_id)
        )

        belongs_to_organization = exists(
            select(1)
            .select_from(PedidoDetalle)
            .join(ProductoVariante, ProductoVariante.id_variante == PedidoDetalle.id_variante)
            .join(Producto, Producto.id_producto == ProductoVariante.id_producto)
            .where(
                PedidoDetalle.id_pedido == Pedido.id_pedido,
                Producto.id_organizacion == organization_id,
            )
        )
        orders_query = select(func.count(func.distinct(Pedido.id_pedido))).where(belongs_to_organization)
        if start_at is not None:
            orders_query = orders_query.where(Pedido.fecha_pedido >= start_at)
        if end_at is not None:
            orders_query = orders_query.where(Pedido.fecha_pedido < end_at)
        order_count = self._scalar(orders_query)

        payment_belongs_to_organization = exists(
            select(1)
            .select_from(PedidoDetalle)
            .join(ProductoVariante, ProductoVariante.id_variante == PedidoDetalle.id_variante)
            .join(Producto, Producto.id_producto == ProductoVariante.id_producto)
            .where(
                PedidoDetalle.id_pedido == Pago.id_pedido,
                Producto.id_organizacion == organization_id,
            )
        )
        sales_query = select(func.coalesce(func.sum(Pago.monto), 0)).where(
            Pago.estado == "PAGADO", payment_belongs_to_organization
        )
        if start_at is not None:
            sales_query = sales_query.where(Pago.fecha_pago >= start_at)
        if end_at is not None:
            sales_query = sales_query.where(Pago.fecha_pago < end_at)
        sales_total = self.db.scalar(sales_query) or 0

        reservation_query = (
            select(func.count(Reserva.id_reserva))
            .join(Inventario, Inventario.id_inventario == Reserva.id_inventario)
            .join(Sucursal, Sucursal.id_sucursal == Inventario.id_sucursal)
            .join(Usuario, Usuario.id_usuario == Reserva.id_usuario)
            .where(
                Sucursal.id_organizacion == organization_id,
                Usuario.id_organizacion == organization_id,
            )
        )
        if start_at is not None:
            reservation_query = reservation_query.where(Reserva.fecha >= start_at)
        if end_at is not None:
            reservation_query = reservation_query.where(Reserva.fecha < end_at)
        reservation_count = self._scalar(reservation_query)

        inventory = self.db.execute(
            select(
                func.coalesce(func.sum(Inventario.stock_disponible), 0),
                func.coalesce(func.sum(Inventario.stock_reservado), 0),
                func.coalesce(func.sum(Inventario.stock_vendido), 0),
            )
            .join(Sucursal, Sucursal.id_sucursal == Inventario.id_sucursal)
            .where(Sucursal.id_organizacion == organization_id)
        ).one()

        return {
            "organizacion_id": organization_id,
            "organizacion_nombre": organization.nombre,
            "periodo_desde": desde,
            "periodo_hasta": hasta,
            "plan_codigo": plan.codigo if plan else None,
            "plan_nombre": plan.nombre if plan else None,
            "estado_suscripcion": latest.estado if latest else "SIN_SUSCRIPCION",
            "fecha_inicio_suscripcion": latest.fecha_inicio if latest else None,
            "fecha_fin_suscripcion": latest.fecha_fin if latest else None,
            "sucursales_activas": branch_count,
            "limite_sucursales": plan.max_sucursales if plan else None,
            "usuarios_activos": active_users,
            "productos_registrados": product_count,
            "pedidos_periodo": order_count,
            "ventas_periodo": sales_total,
            "reservas_periodo": reservation_count,
            "inventario_disponible": int(inventory[0]),
            "inventario_reservado": int(inventory[1]),
            "inventario_vendido": int(inventory[2]),
        }

    def _scalar(self, query) -> int:
        return int(self.db.scalar(query) or 0)
