from datetime import datetime, timezone
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.core.config import settings
from app.models.pago import Pago
from app.models.pedido import Pedido
from app.repositories.payment_repository import PaymentRepository
from app.schemas.payment import CreatePaymentRequest, PaymentResponse
from app.services.stock_sale_service import consume_order_stock, release_order_stock


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
        if order.estado != "PENDIENTE":
            raise AppException("El pedido no está pendiente", status_code=409)
        if request.operation_uuid:
            uuid_payment = self.repository.db.scalar(
                select(Pago).where(Pago.idempotency_key == str(request.operation_uuid))
            )
            if uuid_payment is not None and uuid_payment.id_pedido != order.id_pedido:
                raise AppException("El UUID de pago ya está asociado a otra operación", status_code=409)
        existing = self.repository.get_payment_by_order(request.id_pedido)
        if existing:
            if request.operation_uuid and existing.idempotency_key == str(request.operation_uuid):
                if existing.metodo_pago == request.metodo_pago:
                    return self._to_response(existing)
                raise AppException("El UUID de pago se reutilizó con otro método", status_code=409)
            if existing.estado != "FALLIDO":
                raise AppException("El pedido ya tiene un pago creado", status_code=409)
            existing.estado = "PENDIENTE"
            existing.metodo_pago = request.metodo_pago
            existing.idempotency_key = str(request.operation_uuid) if request.operation_uuid else None
            existing.currency = settings.stripe_currency.upper()
            # A failed Stripe attempt must not leak its provider reference into
            # a subsequent cash/QR selection for the same order.
            if request.metodo_pago != "TARJETA":
                existing.proveedor = None
                existing.referencia_externa = None
                existing.evento_externo = None
            self.repository.db.commit()
            return self._to_response(existing)

        try:
            payment = self.repository.create_payment(
                order.id_pedido, request.metodo_pago, order.total,
                idempotency_key=str(request.operation_uuid) if request.operation_uuid else None,
                currency=settings.stripe_currency.upper(),
            )
            self.repository.db.commit()
            return self._to_response(payment)
        except SQLAlchemyError as exc:
            self.repository.db.rollback()
            raise AppException("No se pudo crear el pago", status_code=500) from exc

    def approve_payment(
        self, id_pago: int, id_cliente: int | None = None, *, allow_retry_from_failed: bool = False
    ) -> PaymentResponse:
        payment = self._get_approvable_payment(id_pago, allow_retry_from_failed=allow_retry_from_failed)
        order = self.repository.get_order_by_id(payment.id_pedido)
        if order is None:
            raise AppException("Pedido no encontrado", status_code=404)
        self._ensure_order_owner(order, id_cliente)
        try:
            if order.estado != "PENDIENTE":
                raise AppException("El pedido no está pendiente", status_code=409)
            consume_order_stock(self.repository.db, order)
            self.repository.update_payment_status(payment, "PAGADO")
            payment.fecha_pago = datetime.now(timezone.utc)
            self.repository.update_order_status(order, "CONFIRMADO")
            self.repository.db.commit()
            return self._to_response(payment)
        except SQLAlchemyError as exc:
            self.repository.db.rollback()
            raise AppException("No se pudo aprobar el pago", status_code=500) from exc

    def reject_payment(self, id_pago: int, id_cliente: int | None = None) -> PaymentResponse:
        payment = self._get_approvable_payment(id_pago)
        order = self.repository.get_order_by_id(payment.id_pedido)
        if order is None:
            raise AppException("Pedido no encontrado", status_code=404)
        self._ensure_order_owner(order, id_cliente)
        try:
            self.repository.update_payment_status(payment, "FALLIDO")
            order.estado = "PENDIENTE"
            release_order_stock(self.repository.db, order, reason=f"Pago {payment.id_pago} rechazado")
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

    def create_stripe_payment(self, id_pedido: int, id_cliente: int | None, intent: dict, *, simulated: bool = False) -> PaymentResponse:
        provider_name = "STRIPE_SIMULADO" if simulated else "STRIPE"
        order = self.repository.get_order_by_id(id_pedido)
        if order is None:
            raise AppException("Pedido no encontrado", status_code=404)
        self._ensure_order_owner(order, id_cliente)
        if order.estado != "PENDIENTE":
            raise AppException("El pedido no está pendiente", status_code=409)
        existing = self.repository.get_payment_by_order(id_pedido)
        if existing and existing.estado not in ("FALLIDO", "CANCELADO"):
            if existing.referencia_externa not in (None, intent["id"]):
                raise AppException("El pedido ya tiene un pago creado", status_code=409)
            if existing.proveedor not in (None, "STRIPE", "STRIPE_SIMULADO"):
                raise AppException("El pedido ya tiene un pago creado", status_code=409)
            if existing.referencia_externa is None:
                existing.proveedor = provider_name
                existing.simulated = simulated
                existing.currency = settings.stripe_currency.upper()
                existing.referencia_externa = intent["id"]
                existing.evento_externo = None
                self.repository.db.commit()
            return self._to_response(existing)
        if existing:
            existing.metodo_pago = "TARJETA"
            existing.proveedor = provider_name
            existing.simulated = simulated
            existing.currency = settings.stripe_currency.upper()
            existing.referencia_externa = intent["id"]
            existing.evento_externo = None
            existing.estado = "PENDIENTE"
            self.repository.db.commit()
            return self._to_response(existing)
        try:
            payment = self.repository.create_payment(
                id_pedido, "TARJETA", order.total, proveedor=provider_name, referencia_externa=intent["id"],
                simulated=simulated, currency=settings.stripe_currency.upper(),
            )
            self.repository.db.commit()
            return self._to_response(payment)
        except SQLAlchemyError as exc:
            self.repository.db.rollback()
            raise AppException("No se pudo registrar el pago Stripe", status_code=500) from exc

    def attach_demo_qr_reference(self, id_pago: int, reference: str) -> PaymentResponse:
        """Marks the generic QR as a demo-only Stripe transaction reference."""
        payment = self.repository.get_payment_by_id(id_pago)
        if payment is None:
            raise AppException("Pago no encontrado", status_code=404)
        payment.proveedor = "STRIPE_SIMULADO"
        payment.referencia_externa = reference
        payment.simulated = True
        payment.currency = settings.stripe_currency.upper()
        self.repository.db.commit()
        return self._to_response(payment)

    def _get_approvable_payment(self, id_pago: int, *, allow_retry_from_failed: bool = False) -> Pago:
        payment = self.repository.get_payment_by_id(id_pago)
        if payment is None:
            raise AppException("Pago no encontrado", status_code=404)
        allowed_states = {"PENDIENTE", "PROCESANDO"}
        if allow_retry_from_failed:
            # Stripe can emit payment_failed for a declined attempt on an
            # intent that the customer later retries successfully.
            allowed_states.add("FALLIDO")
        if payment.estado not in allowed_states:
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
            proveedor=payment.proveedor,
            referencia_externa=payment.referencia_externa,
            currency=payment.currency,
            simulated=payment.simulated,
            cash_received=payment.cash_received,
            cash_change=payment.cash_change,
        )
