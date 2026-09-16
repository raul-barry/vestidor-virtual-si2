from fastapi import APIRouter, Depends, HTTPException
from app.core.config import settings
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database.database import get_db
from app.models.usuario import Usuario
from app.schemas.payment import CreatePaymentRequest, PaymentResponse
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
    current_user: Usuario = Depends(get_current_user),
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
    current_user: Usuario = Depends(get_current_user),
) -> PaymentResponse:
    service, id_cliente = get_payment_service_for_user(db, current_user)
    return service.get_payment(id_pedido, id_cliente)


@payment_router.put(
    "/{id_pago}/approve",
    response_model=PaymentResponse,
    responses={401: {"description": "Token inválido"}, 404: {"description": "Pago o pedido no encontrado"}},
)
def approve_payment(
    id_pago: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
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
    current_user: Usuario = Depends(get_current_user),
) -> PaymentResponse:
    if settings.environment not in ("development", "test"):
        raise HTTPException(403, "Simulación de pagos deshabilitada")
    service, id_cliente = get_payment_service_for_user(db, current_user)
    return service.reject_payment(id_pago, id_cliente)
