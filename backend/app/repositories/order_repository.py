from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.carrito import Carrito
from app.models.pedido import Pedido
from app.models.pedido_detalle import PedidoDetalle
from app.models.producto_variante import ProductoVariante
from app.models.sucursal import Sucursal


class OrderRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_order(self, id_cliente: int, total: Decimal, **delivery_data: object) -> Pedido:
        order = Pedido(id_cliente=id_cliente, estado="PENDIENTE", total=total, **delivery_data)
        self.db.add(order)
        self.db.flush()
        self.db.refresh(order)
        return order

    def create_order_detail(
        self, id_pedido: int, id_variante: int, cantidad: int, precio_unitario: Decimal
    ) -> PedidoDetalle:
        detail = PedidoDetalle(
            id_pedido=id_pedido,
            id_variante=id_variante,
            cantidad=cantidad,
            precio_unitario=precio_unitario,
        )
        self.db.add(detail)
        self.db.flush()
        self.db.refresh(detail)
        return detail

    def get_orders_by_client(self, id_cliente: int) -> list[Pedido]:
        statement = (
            select(Pedido)
            .where(Pedido.id_cliente == id_cliente)
            .options(
                selectinload(Pedido.detalles).joinedload(PedidoDetalle.variante).joinedload(ProductoVariante.producto),
                selectinload(Pedido.detalles).joinedload(PedidoDetalle.variante).joinedload(ProductoVariante.talla),
                selectinload(Pedido.detalles).joinedload(PedidoDetalle.variante).joinedload(ProductoVariante.color),
            )
            .order_by(Pedido.fecha_pedido.desc())
        )
        return list(self.db.scalars(statement).all())

    def get_order_by_id(self, id_pedido: int) -> Pedido | None:
        statement = (
            select(Pedido)
            .where(Pedido.id_pedido == id_pedido)
            .options(
                selectinload(Pedido.detalles).joinedload(PedidoDetalle.variante).joinedload(ProductoVariante.producto),
                selectinload(Pedido.detalles).joinedload(PedidoDetalle.variante).joinedload(ProductoVariante.talla),
                selectinload(Pedido.detalles).joinedload(PedidoDetalle.variante).joinedload(ProductoVariante.color),
            )
        )
        return self.db.scalar(statement)

    def get_active_branch_by_id(self, id_sucursal: int) -> Sucursal | None:
        return self.db.scalar(select(Sucursal).where(Sucursal.id_sucursal == id_sucursal, Sucursal.estado == "ACTIVA"))

    def get_active_branches(self) -> list[Sucursal]:
        return list(self.db.scalars(select(Sucursal).where(Sucursal.estado == "ACTIVA").order_by(Sucursal.nombre)).all())

    def finalize_cart(self, cart: Carrito) -> Carrito:
        cart.estado = "FINALIZADO"
        self.db.flush()
        self.db.refresh(cart)
        return cart
