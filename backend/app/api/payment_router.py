from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from app.core.config import settings
from sqlalchemy.orm import Session

from app.core.security import require_roles
from app.core.exceptions import AppException
from app.database.database import get_db
from app.models.usuario import Usuario
from app.schemas.payment import (
    CreatePaymentRequest,
    PaymentResponse,
    PaymentStatusResponse,
    QRPaymentResponse,
    StripeIntentRequest,
    StripeIntentResponse,
    CreateRefundRequest,
    RefundEvidenceRequest,
    ExchangeChargeRequest,
    SimulatePaymentRequest,
)
from app.models.payment_refund import PaymentRefund
from app.models.payment_adjustment import PaymentAdjustment
from app.models.exchange import GarmentExchange
from app.models.pago import Pago
from app.models.pedido import Pedido
from app.models.cliente import Cliente
from app.services.payment_providers import (
    PaymentProviderError,
    QRPaymentProvider,
    SimulatedStripeCardPaymentProvider,
    StripeCardPaymentProvider,
)
from app.services.payment_service import PaymentService
from app.services.payment_refund_service import PaymentRefundService
from app.services.payment_adjustment_service import PaymentAdjustmentService
from app.services.stock_sale_service import hold_order_stock, release_order_stock
from app.services.audit_service import AuditService

payment_router = APIRouter(prefix="/payments", tags=["Pagos"])


def _payment_organization_id(db: Session, payment: Pago) -> int | None:
    order = db.get(Pedido, payment.id_pedido)
    client = db.get(Cliente, order.id_cliente) if order and order.id_cliente else None
    return client.usuario.id_organizacion if client and client.usuario else None


def get_payment_service_for_user(db: Session, current_user: Usuario) -> tuple[PaymentService, int]:
    service = PaymentService(db)
    return service, service.get_client_id_for_user(current_user.id_usuario)


@payment_router.post(
    "",
    response_model=PaymentResponse,
    responses={
        401: {"description": "Token inválido"},
        404: {"description": "Pedido no encontrado"},
        409: {"description": "El pedido ya tiene un pago creado"},
    },
)
def create_payment(
    request: CreatePaymentRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("CLIENTE")),
) -> PaymentResponse:
    service, id_cliente = get_payment_service_for_user(db, current_user)
    return service.create_payment(request, id_cliente)


@payment_router.get(
    "/order/{id_pedido}",
    response_model=PaymentResponse,
    responses={401: {"description": "Token inválido"}, 404: {"description": "Pago o pedido no encontrado"}},
)
def get_payment(
    id_pedido: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("CLIENTE")),
) -> PaymentResponse:
    service, id_cliente = get_payment_service_for_user(db, current_user)
    return service.get_payment(id_pedido, id_cliente)


@payment_router.post("/stripe/create-intent", response_model=StripeIntentResponse)
def create_stripe_intent(
    request: StripeIntentRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("CLIENTE")),
) -> StripeIntentResponse:
    service, id_cliente = get_payment_service_for_user(db, current_user)
    order = service.repository.get_order_by_id(request.id_pedido)
    if order is None:
        raise HTTPException(404, "Pedido no encontrado")
    service._ensure_order_owner(order, id_cliente)
    existing = service.repository.get_payment_by_order(request.id_pedido)
    simulation = settings.payment_simulation_mode
    try:
        hold_order_stock(db, order)
        db.commit()
        provider = SimulatedStripeCardPaymentProvider() if simulation else StripeCardPaymentProvider()
        intent = (
            provider.retrieve_intent(existing.referencia_externa)
            if existing and existing.estado == "PENDIENTE"
            and existing.proveedor == ("STRIPE_SIMULADO" if simulation else "STRIPE")
            and existing.referencia_externa
            else provider.create_intent(order.total, request.id_pedido)
        )
        payment = service.create_stripe_payment(request.id_pedido, id_cliente, intent, simulated=simulation)
    except PaymentProviderError as exc:
        try:
            db.rollback()
            locked_order = service.repository.get_order_by_id(request.id_pedido)
            if locked_order is not None:
                release_order_stock(db, locked_order, reason="No se pudo iniciar la autorización de pago")
                db.commit()
        except Exception:
            db.rollback()
        raise HTTPException(503, str(exc)) from exc
    return StripeIntentResponse(
        client_secret=intent["client_secret"],
        publishable_key=settings.stripe_publishable_key,
        payment=payment,
        simulation=simulation,
    )


@payment_router.get("/{id_pedido}/status", response_model=PaymentStatusResponse)
def payment_status(
    id_pedido: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("CLIENTE")),
) -> PaymentStatusResponse:
    service, id_cliente = get_payment_service_for_user(db, current_user)
    payment = service.get_payment(id_pedido, id_cliente)
    order = service.repository.get_order_by_id(id_pedido)
    return PaymentStatusResponse(payment=payment, order_status=order.estado)


@payment_router.post("/qr", response_model=QRPaymentResponse)
def create_qr_payment(
    request: CreatePaymentRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("CLIENTE")),
) -> QRPaymentResponse:
    if settings.environment not in ("development", "test") or not settings.payment_simulation_mode:
        raise HTTPException(503, "No hay un proveedor bancario QR real configurado.")
    service, id_cliente = get_payment_service_for_user(db, current_user)
    order = service.repository.get_order_by_id(request.id_pedido)
    if order is None:
        raise HTTPException(404, "Pedido no encontrado")
    service._ensure_order_owner(order, id_cliente)
    hold_order_stock(db, order)
    db.commit()
    payment = service.create_payment(request, id_cliente)
    qr_request = QRPaymentProvider.create_demo_request(payment.id_pedido, payment.monto, settings.stripe_currency)
    payment = service.attach_demo_qr_reference(payment.id_pago, qr_request["reference"])
    return QRPaymentResponse(
        payment=payment,
        qr_payload=qr_request["payload"],
        provider_reference=qr_request["reference"],
    )


@payment_router.post("/qr/{id_pago}/confirm", response_model=PaymentResponse)
def confirm_demo_qr_payment(
    id_pago: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("CLIENTE")),
) -> PaymentResponse:
    """Accept a scan in the QR demo. Real QR confirmation belongs to the bank."""
    if settings.environment not in ("development", "test") or not settings.payment_simulation_mode:
        raise HTTPException(403, "Simulación de pagos QR deshabilitada")
    service, id_cliente = get_payment_service_for_user(db, current_user)
    payment = service.repository.get_payment_by_id(id_pago)
    if payment is None or payment.metodo_pago != "QR" or payment.proveedor != "STRIPE_SIMULADO":
        raise HTTPException(404, "Pago QR de demostración no encontrado")
    return service.approve_payment(id_pago, id_cliente)


@payment_router.post("/stripe/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)) -> dict[str, str]:
    if not settings.stripe_webhook_secret:
        raise HTTPException(503, "Webhook de Stripe no configurado actualmente")
    try:
        import stripe
        payload = await request.body()
        signature = request.headers.get("stripe-signature", "")
        event = stripe.Webhook.construct_event(payload, signature, settings.stripe_webhook_secret)
    except Exception as exc:
        raise HTTPException(400, "Firma de webhook Stripe inválida") from exc

    event_type = event["type"]
    if event_type in {"refund.updated", "charge.refunded"}:
        external = event["data"]["object"]
        if event_type == "refund.updated":
            provider_references = [external.get("id")]
        else:
            provider_references = [
                item.get("id") for item in (external.get("refunds") or {}).get("data", [])
                if isinstance(item, dict) and item.get("id")
            ]
        if not provider_references:
            return {"status": "ignored"}
        refunds = db.scalars(select(PaymentRefund).where(
            PaymentRefund.provider_reference.in_(provider_references),
        ).with_for_update()).all()
        if not refunds:
            return {"status": "ignored"}
        event_key_prefix = f"{event['id']}:"
        if all((row.provider_event_id or "").startswith(event_key_prefix) for row in refunds):
            return {"status": "already_processed"}
        provider_state = external.get("status")
        for refund in refunds:
            refund.provider_event_id = f"{event['id']}:{refund.provider_reference}"
            if event_type == "charge.refunded" or provider_state == "succeeded":
                refund.state = "DEVOLUCION_COMPLETADA"
                refund.processed_at = datetime.now(timezone.utc)
                if refund.exchange_id:
                    exchange = db.get(GarmentExchange, refund.exchange_id)
                    if exchange:
                        exchange.financial_state = "DEVOLUCION_COMPLETADA"
                        if exchange.physical_replacement_delivered:
                            exchange.state = "COMPLETADO"
            elif provider_state in {"failed", "canceled"}:
                refund.state = "DEVOLUCION_RECHAZADA"
                refund.error_message = "Stripe notificó el rechazo de la devolución."
            else:
                refund.state = "DEVOLUCION_PROCESANDO"
            from app.services.audit_service import AuditService
            AuditService.record(db, organization_id=refund.organization_id, actor_id=None, actor_role="SISTEMA",
                action="DEVOLUCION_PROVEEDOR_ACTUALIZADA", entity="PaymentRefund", entity_id=refund.id,
                details={"state": refund.state, "provider": refund.provider},
                dedupe_key=f"refund-webhook:{event['id']}:{refund.provider_reference}")
        db.commit()
        return {"status": "processed"}
    if event_type not in {
        "payment_intent.processing",
        "payment_intent.succeeded",
        "payment_intent.payment_failed",
        "payment_intent.canceled",
    }:
        return {"status": "ignored"}
    intent = event["data"]["object"]
    reference = intent["id"]
    service = PaymentService(db)
    payment = service.repository.get_payment_by_reference(reference)
    if payment is None:
        adjustment = db.scalar(select(PaymentAdjustment).where(
            PaymentAdjustment.provider_reference == reference,
        ).with_for_update())
        if adjustment is None:
            return {"status": "ignored"}
        if adjustment.simulated:
            return {"status": "ignored_simulated_payment"}
        if adjustment.provider_event_id == event["id"]:
            return {"status": "already_processed"}
        adjustment.provider_event_id = event["id"]
        exchange = db.scalar(select(GarmentExchange).where(
            GarmentExchange.id == adjustment.exchange_id
        ).with_for_update())
        if event_type == "payment_intent.processing":
            adjustment.state = "PROCESANDO"
        elif event_type == "payment_intent.succeeded":
            adjustment.state = "COMPLETADO"
            adjustment.confirmed_at = datetime.now(timezone.utc)
            if exchange:
                exchange.financial_state = "COBRO_COMPLETADO"
                exchange.state = "COMPLETADO" if exchange.physical_replacement_delivered else "APROBADO"
        else:
            adjustment.state = "RECHAZADO"
            if exchange:
                exchange.financial_state = "COBRO_RECHAZADO"
                exchange.state = "PENDIENTE_COBRO"
        from app.services.audit_service import AuditService
        AuditService.record(db, organization_id=adjustment.organization_id, actor_id=None,
            actor_role="SISTEMA", action="COBRO_DIFERENCIA_CAMBIO_ACTUALIZADO",
            entity="PaymentAdjustment", entity_id=adjustment.id,
            result=adjustment.state, details={"exchange_id": adjustment.exchange_id,
                "provider": adjustment.provider}, dedupe_key=f"exchange-charge-event:{event['id']}")
        db.commit()
        return {"status": "processed"}
    if payment.simulated:
        return {"status": "ignored_simulated_payment"}
    if payment.evento_externo == event["id"] or payment.estado == "PAGADO":
        return {"status": "already_processed"}
    if event_type == "payment_intent.processing":
        if payment.estado == "PENDIENTE":
            payment.estado = "PROCESANDO"
        payment.evento_externo = event["id"]
        db.commit()
    elif event_type == "payment_intent.succeeded":
        if payment.estado == "CANCELADO":
            payment.estado = "REQUIERE_REVISION"
            payment.evento_externo = event["id"]
            from app.services.audit_service import AuditService
            organization_id = _payment_organization_id(db, payment)
            if organization_id is not None:
                AuditService.record(db, organization_id=organization_id, actor_id=None,
                    actor_role="SISTEMA", action="PAGO_TARDIO_REQUIERE_REVISION",
                    entity="Pago", entity_id=payment.id_pago,
                    details={"provider": payment.proveedor, "state": payment.estado},
                    dedupe_key=f"payment-late-success:{event['id']}")
            db.commit()
            return {"status": "requires_review"}
        payment.evento_externo = event["id"]
        db.flush()
        try:
            service.approve_payment(payment.id_pago, allow_retry_from_failed=True)
        except AppException:
            db.rollback()
            payment = service.repository.get_payment_by_reference(reference)
            if payment is not None:
                payment.estado = "REQUIERE_REVISION"
                payment.evento_externo = event["id"]
                from app.services.audit_service import AuditService
                organization_id = _payment_organization_id(db, payment)
                if organization_id is not None:
                    AuditService.record(db, organization_id=organization_id, actor_id=None,
                        actor_role="SISTEMA", action="PAGO_REQUIERE_REVISION",
                        entity="Pago", entity_id=payment.id_pago,
                        details={"provider": payment.proveedor, "state": payment.estado},
                        dedupe_key=f"payment-review:{event['id']}")
                db.commit()
                return {"status": "requires_review"}
            raise
        except Exception:
            db.rollback()
            raise
    else:
        payment.estado = "CANCELADO" if event_type.endswith("canceled") else "FALLIDO"
        payment.evento_externo = event["id"]
        order = service.repository.get_order_by_id(payment.id_pedido)
        if order is not None:
            release_order_stock(db, order, reason=f"Stripe rechazó/canceló pago {payment.id_pago}")
        db.commit()
    return {"status": "processed"}


def _refund_record(row: PaymentRefund) -> dict:
    return {
        "id": row.id, "payment_id": row.payment_id, "order_id": row.order_id,
        "exchange_id": row.exchange_id, "return_id": row.return_id,
        "operation_uuid": row.operation_uuid, "method": row.method,
        "amount": str(row.amount), "currency": row.currency, "state": row.state,
        "provider": row.provider, "provider_reference": row.provider_reference,
        "reason": row.reason, "evidence_reference": row.evidence_reference,
        "simulated": row.simulated, "error_message": row.error_message,
        "created_at": row.created_at.isoformat(),
        "processed_at": row.processed_at.isoformat() if row.processed_at else None,
    }


@payment_router.post("/refunds", status_code=201)
def create_refund(request: CreateRefundRequest, db: Session = Depends(get_db),
                  actor: Usuario = Depends(require_roles("ADMINISTRADOR", "ENCARGADO_SUCURSAL"))):
    service = PaymentRefundService(db)
    row = service.create(actor=actor, operation_uuid=request.operation_uuid,
        payment_id=request.payment_id, reason=request.reason, method=request.method,
        exchange_id=request.exchange_id, return_id=request.return_id,
        evidence_reference=request.evidence_reference)
    return _refund_record(row)


@payment_router.get("/refunds")
def list_refunds(db: Session = Depends(get_db),
                 actor: Usuario = Depends(require_roles("ADMINISTRADOR", "ENCARGADO_SUCURSAL"))):
    return [_refund_record(row) for row in db.scalars(select(PaymentRefund).order_by(PaymentRefund.created_at.desc()).limit(500)).all()]


@payment_router.post("/refunds/{refund_id}/evidence")
def complete_refund(refund_id: int, request: RefundEvidenceRequest, db: Session = Depends(get_db),
                    actor: Usuario = Depends(require_roles("ADMINISTRADOR", "ENCARGADO_SUCURSAL"))):
    row = db.scalar(select(PaymentRefund).where(PaymentRefund.id == refund_id).with_for_update())
    if row is None:
        raise HTTPException(404, "Devolución monetaria no encontrada.")
    if not request.evidence_reference.strip() or len(request.evidence_reference) > 255:
        raise HTTPException(422, "Registra una referencia de comprobante válida.")
    return _refund_record(PaymentRefundService(db).add_evidence(row, actor, request.evidence_reference))


@payment_router.get("/reconciliation")
def payment_reconciliation(db: Session = Depends(get_db),
                           actor: Usuario = Depends(require_roles("ADMINISTRADOR", "ENCARGADO_SUCURSAL"))):
    rows = db.scalars(select(Pago).where(Pago.estado.in_(("PENDIENTE", "PROCESANDO", "REQUIERE_REVISION")))
        .order_by(Pago.fecha_pago.desc()).limit(500)).all()
    payment_history = db.scalars(select(Pago).order_by(Pago.fecha_pago.desc()).limit(500)).all()
    refunds = db.scalars(select(PaymentRefund)
        .order_by(PaymentRefund.created_at.desc()).limit(500)).all()
    adjustments = db.scalars(select(PaymentAdjustment)
        .order_by(PaymentAdjustment.created_at.desc()).limit(500)).all()
    return {"payments": [PaymentService._to_response(row).model_dump(mode="json") for row in rows],
            "payment_history": [PaymentService._to_response(row).model_dump(mode="json") for row in payment_history],
            "refunds": [_refund_record(row) for row in refunds],
            "adjustments": [{"id": row.id, "exchange_id": row.exchange_id, "amount": str(row.amount),
                "currency": row.currency, "state": row.state, "provider": row.provider,
                "provider_reference": row.provider_reference, "simulated": row.simulated}
                for row in adjustments]}


@payment_router.post("/exchanges/{exchange_id}/charge-intent")
def create_exchange_charge(exchange_id: int, request: ExchangeChargeRequest,
        db: Session = Depends(get_db), actor: Usuario = Depends(require_roles("CLIENTE"))):
    return PaymentAdjustmentService(db).create_intent(exchange_id, request.operation_uuid, actor)


@payment_router.get("/exchanges/{exchange_id}/charge")
def get_exchange_charge(exchange_id: int, db: Session = Depends(get_db),
                        actor: Usuario = Depends(require_roles("CLIENTE"))):
    row = db.scalar(select(PaymentAdjustment).join(GarmentExchange).where(
        PaymentAdjustment.exchange_id == exchange_id,
        GarmentExchange.customer_id == actor.cliente.id_cliente,
    ))
    if row is None:
        raise HTTPException(404, "Cobro de diferencia no encontrado.")
    return PaymentAdjustmentService._response(row, None)


@payment_router.post("/exchanges/{exchange_id}/simulate")
def simulate_exchange_charge(exchange_id: int, approved: bool,
        db: Session = Depends(get_db), actor: Usuario = Depends(require_roles("CLIENTE"))):
    if settings.environment not in {"development", "test"} or not settings.payment_simulation_mode:
        raise HTTPException(403, "Simulación de pago deshabilitada.")
    row = PaymentAdjustmentService(db).confirm_simulated(exchange_id, actor, approved)
    return PaymentAdjustmentService._response(row, None)


@payment_router.put(
    "/{id_pago}/approve",
    response_model=PaymentResponse,
    responses={401: {"description": "Token inválido"}, 404: {"description": "Pago o pedido no encontrado"}},
)
def approve_payment(
    id_pago: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("CLIENTE")),
) -> PaymentResponse:
    if settings.environment not in ("development", "test"):
        raise HTTPException(403, "Simulación de pagos deshabilitada")
    service, id_cliente = get_payment_service_for_user(db, current_user)
    payment = service.repository.get_payment_by_id(id_pago)
    if payment is None:
        raise HTTPException(404, "Pago no encontrado")
    service.get_payment(payment.id_pedido, id_cliente)
    if not payment.simulated:
        raise HTTPException(409, "Solo se puede simular un pago marcado como simulado.")
    return service.approve_payment(id_pago, id_cliente)


@payment_router.put(
    "/{id_pago}/reject",
    response_model=PaymentResponse,
    responses={401: {"description": "Token inválido"}, 404: {"description": "Pago o pedido no encontrado"}},
)
def reject_payment(
    id_pago: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("CLIENTE")),
) -> PaymentResponse:
    if settings.environment not in ("development", "test"):
        raise HTTPException(403, "Simulación de pagos deshabilitada")
    service, id_cliente = get_payment_service_for_user(db, current_user)
    payment = service.repository.get_payment_by_id(id_pago)
    if payment is None:
        raise HTTPException(404, "Pago no encontrado")
    service.get_payment(payment.id_pedido, id_cliente)
    if not payment.simulated:
        raise HTTPException(409, "Solo se puede simular el rechazo de un pago marcado como simulado.")
    return service.reject_payment(id_pago, id_cliente)


@payment_router.put("/reconciliation/{id_pago}/simulate", response_model=PaymentResponse)
def reconcile_simulated_payment(
    id_pago: int,
    request: SimulatePaymentRequest,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(require_roles("ADMINISTRADOR")),
) -> PaymentResponse:
    if settings.environment not in {"development", "test"} or not settings.payment_simulation_mode:
        raise HTTPException(403, "La simulación de pagos está deshabilitada.")
    if actor.id_organizacion is None:
        raise HTTPException(403, "Se requiere contexto de empresa.")
    payment = db.scalar(
        select(Pago).join(Pedido, Pedido.id_pedido == Pago.id_pedido)
        .join(Cliente, Cliente.id_cliente == Pedido.id_cliente)
        .join(Usuario, Usuario.id_usuario == Cliente.id_usuario)
        .where(Pago.id_pago == id_pago, Usuario.id_organizacion == actor.id_organizacion)
        .with_for_update()
    )
    if payment is None:
        raise HTTPException(404, "Pago no encontrado.")
    if not payment.simulated:
        raise HTTPException(409, "Solo se pueden resolver pagos simulados.")

    service = PaymentService(db)
    order_id = payment.id_pedido
    try:
        result = (
            service.approve_payment(id_pago, commit=False)
            if request.approved
            else service.reject_payment(id_pago, commit=False)
        )
        AuditService.record(
            db, organization_id=actor.id_organizacion, actor_id=actor.id_usuario,
            actor_role=actor.rol.nombre,
            action="PAGO_SIMULADO_APROBADO" if request.approved else "PAGO_SIMULADO_RECHAZADO",
            entity="Pago", entity_id=id_pago,
            details={"payment_id": id_pago, "order_id": order_id,
                     "simulated": True, "state": result.estado},
        )
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise
