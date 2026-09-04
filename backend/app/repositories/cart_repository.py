from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.carrito import Carrito
from app.models.carrito_detalle import CarritoDetalle
from app.models.cliente import Cliente
from app.models.producto_variante import ProductoVariante


class CartRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_active_cart_by_client(self, id_cliente: int) -> Carrito | None:
        statement = select(Carrito).where(Carrito.id_cliente == id_cliente, Carrito.estado == "ACTIVO")
        return self.db.scalar(statement)

    def get_client_by_user(self, id_usuario: int) -> Cliente | None:
        statement = select(Cliente).where(Cliente.id_usuario == id_usuario)
        return self.db.scalar(statement)

    def create_cart(self, id_cliente: int) -> Carrito:
        cart = Carrito(id_cliente=id_cliente, estado="ACTIVO")
        self.db.add(cart)
        self.db.flush()
        self.db.refresh(cart)
        return cart

    def get_variant_by_id(self, id_variante: int) -> ProductoVariante | None:
        statement = (
            select(ProductoVariante)
            .where(ProductoVariante.id_variante == id_variante)
            .options(joinedload(ProductoVariante.producto))
        )
        return self.db.scalar(statement)

    def get_item_by_cart_and_variant(self, id_carrito: int, id_variante: int) -> CarritoDetalle | None:
        statement = select(CarritoDetalle).where(
            CarritoDetalle.id_carrito == id_carrito,
            CarritoDetalle.id_variante == id_variante,
        )
        return self.db.scalar(statement)

    def get_item_by_id(self, id_detalle: int) -> CarritoDetalle | None:
        return self.db.get(CarritoDetalle, id_detalle)

    def add_item(
        self, id_carrito: int, id_variante: int, cantidad: int, precio_unitario: Decimal
    ) -> CarritoDetalle:
        item = CarritoDetalle(
            id_carrito=id_carrito,
            id_variante=id_variante,
            cantidad=cantidad,
            precio_unitario=precio_unitario,
        )
        self.db.add(item)
        self.db.flush()
        self.db.refresh(item)
        return item

    def remove_item(self, item: CarritoDetalle) -> None:
        self.db.delete(item)
        self.db.flush()

    def update_quantity(self, item: CarritoDetalle, cantidad: int) -> CarritoDetalle:
        item.cantidad = cantidad
        self.db.flush()
        self.db.refresh(item)
        return item

    def get_cart_items(self, id_carrito: int) -> list[CarritoDetalle]:
        statement = (
            select(CarritoDetalle)
            .where(CarritoDetalle.id_carrito == id_carrito)
            .options(
                joinedload(CarritoDetalle.variante).joinedload(ProductoVariante.producto),
                joinedload(CarritoDetalle.variante).joinedload(ProductoVariante.talla),
                joinedload(CarritoDetalle.variante).joinedload(ProductoVariante.color),
            )
            .order_by(CarritoDetalle.id_detalle)
        )
        return list(self.db.scalars(statement).all())
