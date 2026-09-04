from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.pago import Pago
from app.models.pedido import Pedido
from app.repositories.payment_repository import PaymentRepository
from app.schemas.payment import CreatePaymentRequest, PaymentResponse


class PaymentService:
    def __init__(self, db: Session) -> None:
        self.repository = PaymentRepository(db)

    def get_client_id_for_user(self, id_usuario: int) -> int:
        cliente = self.repository.get_client_by_user(id_usuario)
        if cliente is None:
            raise AppException("Cliente no encontrado", status_code=404)
        return cliente.id_cliente

    def create_payment(self, request: CreatePaymentRequest, id_cliente: int | None = None) -> PaymentResponse:
        order = self.repository.get_order_by_id(request.id_pedido)
        if order is None:
            raise AppException("Pedido no encontrado", status_code=404)
        self._ensure_order_owner(order, id_cliente)
        if self.repository.get_payment_by_order(request.id_pedido):
            raise AppException("El pedido ya tiene un pago creado", status_code=409)

        try:
            payment = self.repository.create_payment(order.id_pedido, request.metodo_pago, order.total)
            self.repository.db.commit()
            return self._to_response(payment)
        except SQLAlchemyError as exc:
            self.repository.db.rollback()
            raise AppException("No se pudo crear el pago", status_code=500) from exc

    def approve_payment(self, id_pago: int, id_cliente: int | None = None) -> PaymentResponse:
        payment = self._get_pending_payment(id_pago)
        order = self.repository.get_order_by_id(payment.id_pedido)
        if order is None:
            raise AppException("Pedido no encontrado", status_code=404)
        self._ensure_order_owner(order, id_cliente)
        try:
            self.repository.update_payment_status(payment, "APROBADO")
            self.repository.update_order_status(order, "CONFIRMADO")
            self.repository.db.commit()
            return self._to_response(payment)
        except SQLAlchemyError as exc:
            self.repository.db.rollback()
            raise AppException("No se pudo aprobar el pago", status_code=500) from exc

    def reject_payment(self, id_pago: int, id_cliente: int | None = None) -> PaymentResponse:
        payment = self._get_pending_payment(id_pago)
        order = self.repository.get_order_by_id(payment.id_pedido)
        if order is None:
            raise AppException("Pedido no encontrado", status_code=404)
        self._ensure_order_owner(order, id_cliente)
        try:
            self.repository.update_payment_status(payment, "RECHAZADO")
            self.repository.db.commit()
            return self._to_response(payment)
        except SQLAlchemyError as exc:
            self.repository.db.rollback()
            raise AppException("No se pudo rechazar el pago", status_code=500) from exc

    def get_payment(self, id_pedido: int, id_cliente: int | None = None) -> PaymentResponse:
        payment = self.repository.get_payment_by_order(id_pedido)
        if payment is None:
            raise AppException("Pago no encontrado", status_code=404)
        order = self.repository.get_order_by_id(id_pedido)
        if order is None:
            raise AppException("Pedido no encontrado", status_code=404)
        self._ensure_order_owner(order, id_cliente)
        return self._to_response(payment)

    def _get_pending_payment(self, id_pago: int) -> Pago:
        payment = self.repository.get_payment_by_id(id_pago)
        if payment is None:
            raise AppException("Pago no encontrado", status_code=404)
        if payment.estado != "PENDIENTE":
            raise AppException("El pago ya fue procesado", status_code=409)
        return payment

    @staticmethod
    def _ensure_order_owner(order: Pedido, id_cliente: int | None) -> None:
        if id_cliente is not None and order.id_cliente != id_cliente:
            raise AppException("Pedido no encontrado", status_code=404)

    @staticmethod
    def _to_response(payment: Pago) -> PaymentResponse:
        return PaymentResponse(
            id_pago=payment.id_pago,
            id_pedido=payment.id_pedido,
            metodo_pago=payment.metodo_pago,
            monto=payment.monto,
            estado=payment.estado,
            fecha_pago=payment.fecha_pago,
        )
