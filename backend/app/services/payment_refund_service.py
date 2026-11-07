from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.comercio import Devolucion
from app.models.exchange import GarmentExchange
from app.models.pago import Pago
from app.models.pedido import Pedido
from app.models.pedido_detalle import PedidoDetalle
from app.models.payment_refund import PaymentRefund
from app.models.usuario import Usuario
from app.services.audit_service import AuditService
from app.services.payment_providers import PaymentProviderError, StripeCardPaymentProvider


class PaymentRefundService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, *, actor: Usuario, operation_uuid: UUID, payment_id: int,
               reason: str, method: str, exchange_id: int | None = None,
               return_id: int | None = None, evidence_reference: str | None = None) -> PaymentRefund:
        if (exchange_id is None) == (return_id is None):
            raise HTTPException(422, "Indica exactamente un cambio de prenda o devolución física.")
        if method not in {"MEDIO_ORIGINAL", "EFECTIVO", "TRANSFERENCIA"}:
            raise HTTPException(422, "Método de devolución no válido.")
        uuid_text = str(operation_uuid)
        existing = self.db.scalar(select(PaymentRefund).where(
            PaymentRefund.organization_id == actor.id_organizacion,
            PaymentRefund.operation_uuid == uuid_text,
        ).with_for_update())
        if existing:
            if (existing.payment_id != payment_id or existing.exchange_id != exchange_id
                    or existing.return_id != return_id or existing.method != method
                    or existing.reason != reason.strip()
                    or existing.evidence_reference != evidence_reference):
                raise HTTPException(409, "El UUID de devolución ya se usó con contenido diferente.")
            if (existing.method == "MEDIO_ORIGINAL" and existing.provider == "STRIPE"
                    and existing.state == "REQUIERE_REVISION" and not existing.provider_reference):
                payment = self.db.scalar(select(Pago).where(
                    Pago.id_pago == existing.payment_id,
                ).with_for_update())
                if payment is None or not payment.referencia_externa:
                    raise HTTPException(409, "No se puede recuperar la referencia del pago Stripe original.")
                existing.state = "DEVOLUCION_PROCESANDO"
                existing.error_message = None
                self.db.commit()
                try:
                    result = StripeCardPaymentProvider().refund_intent(
                        payment.referencia_externa, existing.amount, uuid_text)
                    existing.provider_reference = result["id"]
                    existing.state = ("DEVOLUCION_COMPLETADA" if result["status"] == "succeeded"
                                      else "DEVOLUCION_PROCESANDO")
                    if existing.state == "DEVOLUCION_COMPLETADA":
                        existing.processed_at = datetime.now(timezone.utc)
                        exchange = self.db.get(GarmentExchange, existing.exchange_id) if existing.exchange_id else None
                        self._complete_exchange_refund(exchange)
                except PaymentProviderError as exc:
                    existing.state = "REQUIERE_REVISION"
                    existing.error_message = str(exc)
                self.db.commit()
                self.db.refresh(existing)
            return existing

        payment = self.db.scalar(select(Pago).where(Pago.id_pago == payment_id).with_for_update())
        if payment is None or payment.estado != "PAGADO":
            raise HTTPException(409, "Solo se puede devolver un pago confirmado.")
        order = self.db.scalar(select(Pedido).where(Pedido.id_pedido == payment.id_pedido).with_for_update())
        if order is None:
            raise HTTPException(404, "Pedido asociado al pago no encontrado.")

        exchange = None
        returned = None
        if exchange_id is not None:
            exchange = self.db.scalar(select(GarmentExchange).where(GarmentExchange.id == exchange_id).with_for_update())
            if (exchange is None or exchange.original_order_id != order.id_pedido
                    or exchange.economic_difference is None or exchange.economic_difference >= 0
                    or exchange.financial_state not in {"PENDIENTE_DEVOLUCION", "DEVOLUCION_PENDIENTE"}):
                raise HTTPException(409, "El cambio no tiene una devolución pendiente asociada a este pago.")
            amount = abs(Decimal(exchange.economic_difference))
        else:
            returned = self.db.scalar(select(Devolucion).where(Devolucion.id_devolucion == return_id).with_for_update())
            detail = self.db.scalar(select(PedidoDetalle).where(PedidoDetalle.id_detalle == returned.id_detalle).with_for_update()) if returned else None
            if returned is None or detail is None or detail.id_pedido != order.id_pedido:
                raise HTTPException(404, "La devolución física no corresponde a este pago.")
            amount = (Decimal(detail.precio_unitario) * returned.cantidad).quantize(Decimal("0.01"))

        source_filter = (PaymentRefund.exchange_id == exchange_id if exchange_id is not None
                         else PaymentRefund.return_id == return_id)
        prior_source_refund = self.db.scalar(select(PaymentRefund).where(
            PaymentRefund.organization_id == actor.id_organizacion,
            source_filter,
            PaymentRefund.state != "DEVOLUCION_RECHAZADA",
        ).with_for_update())
        if prior_source_refund is not None:
            raise HTTPException(409, "Esta devolución ya tiene una operación monetaria registrada.")

        refunded = self.db.scalar(select(func.coalesce(func.sum(PaymentRefund.amount), 0)).where(
            PaymentRefund.payment_id == payment.id_pago,
            PaymentRefund.state.in_(("DEVOLUCION_PENDIENTE", "DEVOLUCION_PROCESANDO", "DEVOLUCION_COMPLETADA", "REQUIERE_REVISION")),
        )) or Decimal("0.00")
        if amount <= 0 or Decimal(refunded) + amount > Decimal(payment.monto):
            raise HTTPException(409, "El importe excede el saldo realmente pagado disponible para devolución.")

        provider = payment.proveedor
        state = "DEVOLUCION_PENDIENTE"
        simulated = False
        if method == "MEDIO_ORIGINAL" and payment.simulated:
            if settings.environment not in {"development", "test"} or not settings.payment_simulation_mode:
                raise HTTPException(409, "No se procesan reembolsos bancarios de pagos simulados.")
            state, simulated = "DEVOLUCION_COMPLETADA", True
        elif method == "MEDIO_ORIGINAL" and payment.metodo_pago == "TARJETA" and provider == "STRIPE":
            if not payment.referencia_externa:
                raise HTTPException(409, "El pago no tiene referencia Stripe verificable.")
            state = "DEVOLUCION_PROCESANDO"
        elif method == "MEDIO_ORIGINAL":
            state = "REQUIERE_REVISION"
        elif evidence_reference:
            state = "DEVOLUCION_COMPLETADA"

        row = PaymentRefund(
            organization_id=actor.id_organizacion, payment_id=payment.id_pago,
            order_id=order.id_pedido, exchange_id=exchange_id, return_id=return_id,
            requested_by=actor.id_usuario, operation_uuid=uuid_text, method=method,
            amount=amount, currency=payment.currency, state=state, provider=provider,
            reason=reason.strip(), evidence_reference=evidence_reference,
            simulated=simulated,
            processed_at=datetime.now(timezone.utc) if state == "DEVOLUCION_COMPLETADA" else None,
        )
        self.db.add(row)
        self.db.flush()
        AuditService.record(self.db, organization_id=actor.id_organizacion, actor_id=actor.id_usuario,
            actor_role=actor.rol.nombre, action="DEVOLUCION_MONETARIA_SOLICITADA", entity="PaymentRefund",
            entity_id=row.id, details={"payment_id": payment.id_pago, "order_id": order.id_pedido,
                "amount": str(amount), "currency": payment.currency, "method": method,
                "state": state, "simulated": simulated}, dedupe_key=f"payment-refund:{actor.id_organizacion}:{uuid_text}")
        if state == "DEVOLUCION_COMPLETADA":
            self._complete_exchange_refund(exchange)
        self.db.commit()
        self.db.refresh(row)

        # The external call occurs only after the durable idempotency record is committed.
        if state == "DEVOLUCION_PROCESANDO":
            try:
                result = StripeCardPaymentProvider().refund_intent(payment.referencia_externa, amount, uuid_text)
                row.provider_reference = result["id"]
                if result["status"] == "succeeded":
                    row.state = "DEVOLUCION_COMPLETADA"
                    row.processed_at = datetime.now(timezone.utc)
                    self._complete_exchange_refund(exchange)
                else:
                    row.state = "DEVOLUCION_PROCESANDO"
            except PaymentProviderError as exc:
                row.state = "REQUIERE_REVISION"
                row.error_message = str(exc)
            self.db.commit()
            self.db.refresh(row)
        return row

    def add_evidence(self, row: PaymentRefund, actor: Usuario, evidence_reference: str) -> PaymentRefund:
        if row.state == "DEVOLUCION_COMPLETADA":
            if row.evidence_reference == evidence_reference:
                return row
            raise HTTPException(409, "La devolución ya está completada.")
        if row.method == "MEDIO_ORIGINAL":
            raise HTTPException(409, "La devolución al medio original requiere confirmación del proveedor.")
        row.evidence_reference = evidence_reference.strip()
        row.state = "DEVOLUCION_COMPLETADA"
        row.processed_at = datetime.now(timezone.utc)
        exchange = self.db.get(GarmentExchange, row.exchange_id) if row.exchange_id else None
        self._complete_exchange_refund(exchange)
        AuditService.record(self.db, organization_id=actor.id_organizacion, actor_id=actor.id_usuario,
            actor_role=actor.rol.nombre, action="DEVOLUCION_MONETARIA_DOCUMENTADA", entity="PaymentRefund",
            entity_id=row.id, details={"method": row.method, "state": row.state},
            dedupe_key=f"payment-refund-evidence:{row.id}")
        self.db.commit()
        self.db.refresh(row)
        return row

    def _complete_exchange_refund(self, exchange: GarmentExchange | None) -> None:
        if exchange is None:
            return
        exchange.financial_state = "DEVOLUCION_COMPLETADA"
        if exchange.physical_replacement_delivered:
            exchange.state = "COMPLETADO"
