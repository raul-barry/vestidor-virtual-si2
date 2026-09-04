from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.bitacora import Bitacora
from app.models.cliente import Cliente
from app.models.pago import Pago
from app.models.pedido import Pedido
from app.models.pedido_detalle import PedidoDetalle
from app.models.producto_variante import ProductoVariante


class OrderAdminRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all_orders(self) -> list[Pedido]:
        statement = (
            select(Pedido)
            .options(joinedload(Pedido.cliente).joinedload(Cliente.usuario))
            .order_by(Pedido.fecha_pedido.desc())
        )
        return list(self.db.scalars(statement).all())

    def get_order_by_id(self, id_pedido: int) -> Pedido | None:
        statement = (
            select(Pedido)
            .where(Pedido.id_pedido == id_pedido)
            .options(
                joinedload(Pedido.cliente).joinedload(Cliente.usuario),
                selectinload(Pedido.detalles).joinedload(PedidoDetalle.variante).joinedload(ProductoVariante.producto),
                selectinload(Pedido.detalles).joinedload(PedidoDetalle.variante).joinedload(ProductoVariante.talla),
                selectinload(Pedido.detalles).joinedload(PedidoDetalle.variante).joinedload(ProductoVariante.color),
            )
        )
        return self.db.scalar(statement)

    def update_order_status(self, order: Pedido, estado: str) -> Pedido:
        order.estado = estado
        self.db.flush()
        self.db.refresh(order)
        return order

    def filter_orders_by_status(self, estado: str) -> list[Pedido]:
        statement = (
            select(Pedido)
            .where(Pedido.estado == estado)
            .options(joinedload(Pedido.cliente).joinedload(Cliente.usuario))
            .order_by(Pedido.fecha_pedido.desc())
        )
        return list(self.db.scalars(statement).all())

    def get_payment_by_order(self, id_pedido: int) -> Pago | None:
        statement = select(Pago).where(Pago.id_pedido == id_pedido)
        return self.db.scalar(statement)

    def create_status_audit(self, id_usuario: int, accion: str) -> Bitacora:
        audit = Bitacora(id_usuario=id_usuario, accion=accion)
        self.db.add(audit)
        self.db.flush()
        self.db.refresh(audit)
        return audit
