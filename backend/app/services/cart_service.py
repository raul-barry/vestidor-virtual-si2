from decimal import Decimal

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.carrito import Carrito
from app.repositories.cart_repository import CartRepository
from app.schemas.cart import CartItemResponse, CartResponse


class CartService:
    def __init__(self, db: Session) -> None:
        self.repository = CartRepository(db)

    def get_cart(self, id_cliente: int) -> CartResponse:
        try:
            cart = self._get_or_create_active_cart(id_cliente)
            self.repository.db.commit()
            return self._to_response(cart)
        except SQLAlchemyError as exc:
            self.repository.db.rollback()
            raise AppException("No se pudo obtener el carrito", status_code=500) from exc

    def get_client_id_for_user(self, id_usuario: int) -> int:
        cliente = self.repository.get_client_by_user(id_usuario)
        if cliente is None:
            raise AppException("Cliente no encontrado", status_code=404)
        return cliente.id_cliente

    def add_item(self, id_cliente: int, id_variante: int, cantidad: int) -> CartResponse:
        if cantidad <= 0:
            raise AppException("La cantidad debe ser mayor a cero", status_code=422)

        variante = self.repository.get_variant_by_id(id_variante)
        if variante is None:
            raise AppException("Variante no encontrada", status_code=404)

        try:
            cart = self._get_or_create_active_cart(id_cliente)
            item = self.repository.get_item_by_cart_and_variant(cart.id_carrito, id_variante)
            if item is None:
                self.repository.add_item(cart.id_carrito, id_variante, cantidad, variante.producto.precio_base)
            else:
                self.repository.update_quantity(item, item.cantidad + cantidad)
            self.repository.db.commit()
            return self._to_response(cart)
        except SQLAlchemyError as exc:
            self.repository.db.rollback()
            raise AppException("No se pudo agregar el producto al carrito", status_code=500) from exc

    def update_quantity(self, id_cliente: int, id_detalle: int, cantidad: int) -> CartResponse:
        if cantidad <= 0:
            raise AppException("La cantidad debe ser mayor a cero", status_code=422)

        try:
            cart = self._get_or_create_active_cart(id_cliente)
            item = self.repository.get_item_by_id(id_detalle)
            if item is None or item.id_carrito != cart.id_carrito:
                raise AppException("Producto no encontrado en el carrito", status_code=404)
            self.repository.update_quantity(item, cantidad)
            self.repository.db.commit()
            return self._to_response(cart)
        except SQLAlchemyError as exc:
            self.repository.db.rollback()
            raise AppException("No se pudo actualizar el carrito", status_code=500) from exc

    def remove_item(self, id_cliente: int, id_detalle: int) -> CartResponse:
        try:
            cart = self._get_or_create_active_cart(id_cliente)
            item = self.repository.get_item_by_id(id_detalle)
            if item is None or item.id_carrito != cart.id_carrito:
                raise AppException("Producto no encontrado en el carrito", status_code=404)
            self.repository.remove_item(item)
            self.repository.db.commit()
            return self._to_response(cart)
        except SQLAlchemyError as exc:
            self.repository.db.rollback()
            raise AppException("No se pudo eliminar el producto del carrito", status_code=500) from exc

    # Compatibility aliases for existing service-level callers.
    def add_product(self, id_cliente: int, id_variante: int, cantidad: int) -> CartResponse:
        return self.add_item(id_cliente, id_variante, cantidad)

    def update_item_quantity(self, id_cliente: int, id_detalle: int, cantidad: int) -> CartResponse:
        return self.update_quantity(id_cliente, id_detalle, cantidad)

    def _get_or_create_active_cart(self, id_cliente: int) -> Carrito:
        return self.repository.get_active_cart_by_client(id_cliente) or self.repository.create_cart(id_cliente)

    def _to_response(self, cart: Carrito) -> CartResponse:
        items = [
            CartItemResponse(
                id_detalle=item.id_detalle,
                producto=item.variante.producto.nombre,
                talla=item.variante.talla.nombre,
                color=item.variante.color.nombre,
                cantidad=item.cantidad,
                precio_unitario=item.precio_unitario,
            )
            for item in self.repository.get_cart_items(cart.id_carrito)
        ]
        total = sum((item.precio_unitario * item.cantidad for item in items), Decimal("0"))
        return CartResponse(id_carrito=cart.id_carrito, estado=cart.estado, items=items, total=total)
