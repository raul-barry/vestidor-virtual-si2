from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.exchange import GarmentExchange
from app.models.pago import Pago
from app.models.payment_adjustment import PaymentAdjustment
from app.models.usuario import Usuario
from app.services.audit_service import AuditService
from app.services.payment_providers import PaymentProviderError, SimulatedStripeCardPaymentProvider, StripeCardPaymentProvider


class PaymentAdjustmentService:
    def __init__(self, db: Session):
        self.db = db

    def create_intent(self, exchange_id: int, operation_uuid: UUID, actor: Usuario) -> dict:
        exchange = self.db.scalar(select(GarmentExchange).where(
            GarmentExchange.id == exchange_id
        ).with_for_update())
        if (actor.cliente is None or exchange is None
                or exchange.organization_id != actor.id_organizacion
                or exchange.customer_id != actor.cliente.id_cliente):
            raise HTTPException(404, "Cambio de prenda no encontrado.")
        if exchange.economic_difference is None or exchange.economic_difference <= 0:
            raise HTTPException(409, "El cambio no tiene un importe pendiente de cobro.")
        if exchange.financial_state not in {"PENDIENTE_COBRO", "COBRO_RECHAZADO", "REQUIERE_REVISION"}:
            raise HTTPException(409, "El importe del cambio ya está conciliado.")
        payment = self.db.scalar(select(Pago).where(
            Pago.id_pedido == exchange.original_order_id, Pago.estado == "PAGADO"
        ).with_for_update())
        if payment is None:
            raise HTTPException(409, "La venta original no tiene un pago confirmado.")

        existing = self.db.scalar(select(PaymentAdjustment).where(
            PaymentAdjustment.exchange_id == exchange.id
        ).with_for_update())
        uuid_text = str(operation_uuid)
        if existing:
            if existing.operation_uuid != uuid_text:
                raise HTTPException(409, "El cambio ya tiene una solicitud de cobro.")
            if existing.state == "COMPLETADO":
                return self._response(existing, None)
            if existing.provider_reference and existing.simulated == settings.payment_simulation_mode:
                if existing.simulated:
                    return self._response(existing, f"{existing.provider_reference}_secret_demo")
                try:
                    intent = StripeCardPaymentProvider().retrieve_intent(existing.provider_reference)
                    return self._response(existing, intent["client_secret"])
                except PaymentProviderError:
                    pass
        else:
            existing = PaymentAdjustment(
                organization_id=actor.id_organizacion, exchange_id=exchange.id,
                original_payment_id=payment.id_pago, operation_uuid=uuid_text,
                amount=exchange.economic_difference, currency=payment.currency,
                state="PENDIENTE", provider="STRIPE_SIMULADO" if settings.payment_simulation_mode else "STRIPE",
                simulated=settings.payment_simulation_mode,
            )
            self.db.add(existing)
            self.db.flush([existing])
            AuditService.record(self.db, organization_id=actor.id_organizacion, actor_id=actor.id_usuario,
                actor_role=actor.rol.nombre, action="COBRO_DIFERENCIA_CAMBIO_SOLICITADO",
                entity="PaymentAdjustment", entity_id=existing.id,
                details={"exchange_id": exchange.id, "amount": str(existing.amount),
                         "currency": existing.currency, "simulated": existing.simulated},
                dedupe_key=f"payment-adjustment:{actor.id_organizacion}:{uuid_text}")
            self.db.commit()
            self.db.refresh(existing)

        # The provider call happens only after the durable, tenant-scoped idempotency row is committed.
        try:
            provider = SimulatedStripeCardPaymentProvider() if settings.payment_simulation_mode else StripeCardPaymentProvider()
            intent = (provider.create_intent(existing.amount, exchange.id) if settings.payment_simulation_mode
                      else provider.create_exchange_intent(existing.amount, existing.currency, exchange.id, existing.operation_uuid))
            existing.provider_reference = intent["id"]
            existing.state = "PENDIENTE"
            self.db.commit()
            self.db.refresh(existing)
            return self._response(existing, intent["client_secret"])
        except PaymentProviderError as error:
            existing.state = "REQUIERE_REVISION"
            self.db.commit()
            raise HTTPException(503, str(error)) from error

    def confirm_simulated(self, exchange_id: int, actor: Usuario, approved: bool) -> PaymentAdjustment:
        if actor.cliente is None:
            raise HTTPException(404, "Cliente no encontrado.")
        row = self.db.scalar(select(PaymentAdjustment).where(
            PaymentAdjustment.exchange_id == exchange_id,
            PaymentAdjustment.organization_id == actor.id_organizacion,
        ).with_for_update())
        if row is None or not row.simulated:
            raise HTTPException(404, "Cobro simulado no encontrado.")
        exchange = self.db.scalar(select(GarmentExchange).where(
            GarmentExchange.id == exchange_id,
            GarmentExchange.organization_id == actor.id_organizacion,
            GarmentExchange.customer_id == actor.cliente.id_cliente,
        ).with_for_update())
        if exchange is None:
            raise HTTPException(404, "Cambio de prenda no encontrado.")
        if row.state == "COMPLETADO":
            return row
        row.state = "COMPLETADO" if approved else "RECHAZADO"
        if approved:
            row.confirmed_at = datetime.now(timezone.utc)
            exchange.financial_state = "COBRO_COMPLETADO"
            exchange.state = "COMPLETADO" if exchange.physical_replacement_delivered else "APROBADO"
        else:
            exchange.financial_state = "COBRO_RECHAZADO"
            exchange.state = "PENDIENTE_COBRO"
        AuditService.record(self.db, organization_id=actor.id_organizacion, actor_id=actor.id_usuario,
            actor_role=actor.rol.nombre, action="COBRO_DIFERENCIA_CAMBIO_SIMULADO", entity="PaymentAdjustment",
            entity_id=row.id, result=row.state, details={"exchange_id": exchange.id, "simulated": True},
            dedupe_key=f"payment-adjustment-sim:{row.id}:{row.state}")
        self.db.commit()
        self.db.refresh(row)
        return row

    @staticmethod
    def _response(row: PaymentAdjustment, client_secret: str | None) -> dict:
        return {"id": row.id, "exchange_id": row.exchange_id,
                "operation_uuid": row.operation_uuid, "amount": str(row.amount),
                "currency": row.currency, "state": row.state, "simulated": row.simulated,
                "provider_reference": row.provider_reference, "client_secret": client_secret}
