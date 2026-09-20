from fastapi import APIRouter, Depends, HTTPException, Request
from app.core.config import settings
from sqlalchemy.orm import Session

from app.core.security import require_roles
from app.database.database import get_db
from app.models.usuario import Usuario
from app.schemas.payment import (
    CreatePaymentRequest,
    PaymentResponse,
    PaymentStatusResponse,
    StripeIntentRequest,
    StripeIntentResponse,
)
from app.services.payment_providers import PaymentProviderError, QRPaymentProvider, StripeCardPaymentProvider
from app.services.payment_service import PaymentService

payment_router = APIRouter(prefix="/payments", tags=["Pagos"])


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
    try:
        provider = StripeCardPaymentProvider()
        intent = (
            provider.retrieve_intent(existing.referencia_externa)
            if existing and existing.estado == "PENDIENTE" and existing.proveedor == "STRIPE" and existing.referencia_externa
            else provider.create_intent(order.total, request.id_pedido)
        )
        payment = service.create_stripe_payment(request.id_pedido, id_cliente, intent)
    except PaymentProviderError as exc:
        raise HTTPException(503, str(exc)) from exc
    return StripeIntentResponse(
        client_secret=intent["client_secret"],
        publishable_key=settings.stripe_publishable_key,
        payment=payment,
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


@payment_router.post("/qr", response_model=PaymentResponse)
def create_qr_payment(
    request: CreatePaymentRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("CLIENTE")),
) -> PaymentResponse:
    if not QRPaymentProvider.configured:
        raise HTTPException(503, QRPaymentProvider.unavailable_message())
    service, id_cliente = get_payment_service_for_user(db, current_user)
    return service.create_payment(request, id_cliente)


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
        return {"status": "ignored"}
    if payment.evento_externo == event["id"] or payment.estado == "PAGADO":
        return {"status": "already_processed"}
    if event_type == "payment_intent.processing":
        if payment.estado == "PENDIENTE":
            payment.estado = "PROCESANDO"
        payment.evento_externo = event["id"]
        db.commit()
    elif event_type == "payment_intent.succeeded":
        if payment.estado == "CANCELADO":
            return {"status": "already_processed"}
        payment.evento_externo = event["id"]
        db.flush()
        try:
            service.approve_payment(payment.id_pago, allow_retry_from_failed=True)
        except Exception:
            db.rollback()
            raise
    else:
        payment.estado = "CANCELADO" if event_type.endswith("canceled") else "FALLIDO"
        payment.evento_externo = event["id"]
        db.commit()
    return {"status": "processed"}


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
    return service.reject_payment(id_pago, id_cliente)
