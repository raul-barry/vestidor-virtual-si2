from decimal import Decimal

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.pedido import Pedido
from app.repositories.cart_repository import CartRepository
from app.repositories.order_repository import OrderRepository
from app.schemas.order import OrderDetailResponse, OrderItemResponse


class OrderService:
    def __init__(self, db: Session) -> None:
        self.cart_repository = CartRepository(db)
        self.repository = OrderRepository(db)

    def get_client_id_for_user(self, id_usuario: int) -> int:
        cliente = self.cart_repository.get_client_by_user(id_usuario)
        if cliente is None:
            raise AppException("Cliente no encontrado", status_code=404)
        return cliente.id_cliente

    def create_order_from_cart(self, id_cliente: int) -> OrderDetailResponse:
        cart = self.cart_repository.get_active_cart_by_client(id_cliente)
        if cart is None:
            raise AppException("Carrito activo no encontrado", status_code=404)

        cart_items = self.cart_repository.get_cart_items(cart.id_carrito)
        if not cart_items:
            raise AppException("No se puede crear un pedido con un carrito vacío", status_code=400)

        for item in cart_items:
            if item.variante.estado != "ACTIVO" or item.variante.producto.estado != "ACTIVO":
                raise AppException("Producto no disponible", status_code=409)
        total = sum((item.precio_unitario * item.cantidad for item in cart_items), Decimal("0"))
        try:
            order = self.repository.create_order(id_cliente, total)
            for item in cart_items:
                self.repository.create_order_detail(
                    order.id_pedido,
                    item.id_variante,
                    item.cantidad,
                    item.precio_unitario,
                )
            self.repository.finalize_cart(cart)
            self.repository.db.commit()
            return self._to_response(order.id_pedido)
        except SQLAlchemyError as exc:
            self.repository.db.rollback()
            raise AppException("No se pudo crear el pedido", status_code=500) from exc

    def get_client_orders(self, id_cliente: int) -> list[OrderDetailResponse]:
        return [self._order_to_response(order) for order in self.repository.get_orders_by_client(id_cliente)]

    def get_order_detail(self, id_cliente: int, id_pedido: int) -> OrderDetailResponse:
        order = self.repository.get_order_by_id(id_pedido)
        if order is None or order.id_cliente != id_cliente:
            raise AppException("Pedido no encontrado", status_code=404)
        return self._order_to_response(order)

    def _to_response(self, id_pedido: int) -> OrderDetailResponse:
        order = self.repository.get_order_by_id(id_pedido)
        if order is None:
            raise AppException("Pedido no encontrado", status_code=404)
        return self._order_to_response(order)

    @staticmethod
    def _order_to_response(order: Pedido) -> OrderDetailResponse:
        return OrderDetailResponse(
            id_pedido=order.id_pedido,
            fecha_pedido=order.fecha_pedido,
            estado=order.estado,
            total=order.total,
            detalles=[
                OrderItemResponse(
                    producto=detail.variante.producto.nombre,
                    talla=detail.variante.talla.nombre,
                    color=detail.variante.color.nombre,
                    cantidad=detail.cantidad,
                    precio_unitario=detail.precio_unitario,
                )
                for detail in order.detalles
            ],
        )
