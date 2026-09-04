from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.pedido import Pedido
from app.repositories.order_admin_repository import OrderAdminRepository
from app.schemas.order_admin import (
    OrderAdminDetailResponse,
    OrderAdminItemResponse,
    OrderAdminResponse,
    OrderPaymentResponse,
)


class OrderAdminService:
    VALID_STATES = {"PENDIENTE", "CONFIRMADO", "PREPARANDO", "ENVIADO", "ENTREGADO", "CANCELADO"}
    TRANSITIONS = {
        "PENDIENTE": {"CONFIRMADO", "CANCELADO"},
        "CONFIRMADO": {"PREPARANDO", "CANCELADO"},
        "PREPARANDO": {"ENVIADO", "CANCELADO"},
        "ENVIADO": {"ENTREGADO", "CANCELADO"},
        "ENTREGADO": set(),
        "CANCELADO": set(),
    }

    def __init__(self, db: Session) -> None:
        self.repository = OrderAdminRepository(db)

    def list_orders(self, estado: str | None = None) -> list[OrderAdminResponse]:
        if estado is not None and estado not in self.VALID_STATES:
            raise AppException("Estado de pedido no válido", status_code=422)
        orders = self.repository.filter_orders_by_status(estado) if estado else self.repository.get_all_orders()
        return [self._to_summary(order) for order in orders]

    def get_order_detail(self, id_pedido: int) -> OrderAdminDetailResponse:
        order = self._get_order(id_pedido)
        payment = self.repository.get_payment_by_order(id_pedido)
        return OrderAdminDetailResponse(
            **self._to_summary(order).model_dump(),
            detalles=[
                OrderAdminItemResponse(
                    producto=detail.variante.producto.nombre,
                    talla=detail.variante.talla.nombre,
                    color=detail.variante.color.nombre,
                    cantidad=detail.cantidad,
                    precio_unitario=detail.precio_unitario,
                )
                for detail in order.detalles
            ],
            pago=OrderPaymentResponse(
                id_pago=payment.id_pago,
                metodo_pago=payment.metodo_pago,
                monto=payment.monto,
                estado=payment.estado,
            ) if payment else None,
        )

    def change_status(self, id_pedido: int, new_state: str, id_usuario: int) -> OrderAdminResponse:
        if new_state not in self.VALID_STATES:
            raise AppException("Estado de pedido no válido", status_code=422)
        order = self._get_order(id_pedido)
        old_state = order.estado
        if new_state not in self.TRANSITIONS.get(old_state, set()):
            raise AppException("Transición de estado no permitida", status_code=422)

        try:
            order = self.repository.update_order_status(order, new_state)
            self.repository.create_status_audit(
                id_usuario,
                f"Pedido {order.id_pedido}: estado {old_state} -> {new_state}",
            )
            self.repository.db.commit()
            return self._to_summary(order)
        except SQLAlchemyError as exc:
            self.repository.db.rollback()
            raise AppException("No se pudo actualizar el estado del pedido", status_code=500) from exc

    def _get_order(self, id_pedido: int) -> Pedido:
        order = self.repository.get_order_by_id(id_pedido)
        if order is None:
            raise AppException("Pedido no encontrado", status_code=404)
        return order

    @staticmethod
    def _to_summary(order: Pedido) -> OrderAdminResponse:
        return OrderAdminResponse(
            id_pedido=order.id_pedido,
            cliente=f"{order.cliente.usuario.nombres} {order.cliente.usuario.apellidos}",
            fecha=order.fecha_pedido,
            estado=order.estado,
            total=order.total,
        )
