from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class CreatePaymentRequest(BaseModel):
    id_pedido: int
    metodo_pago: Literal["EFECTIVO", "QR", "TARJETA"]
    operation_uuid: UUID | None = None


PaymentState = Literal["PENDIENTE", "PROCESANDO", "PAGADO", "FALLIDO", "CANCELADO", "REQUIERE_REVISION"]


class PaymentResponse(BaseModel):
    id_pago: int
    id_pedido: int
    metodo_pago: str
    monto: Decimal
    estado: PaymentState
    fecha_pago: datetime
    proveedor: str | None = None
    referencia_externa: str | None = None
    currency: str = "BOB"
    simulated: bool = False
    cash_received: Decimal | None = None
    cash_change: Decimal = Decimal("0.00")


class StripeIntentRequest(BaseModel):
    id_pedido: int


class StripeIntentResponse(BaseModel):
    client_secret: str
    publishable_key: str
    payment: PaymentResponse
    simulation: bool = False


class QRPaymentResponse(BaseModel):
    payment: PaymentResponse
    qr_payload: str
    provider_reference: str
    simulation: bool = True


class PaymentStatusResponse(BaseModel):
    payment: PaymentResponse
    order_status: str


class CreateRefundRequest(BaseModel):
    operation_uuid: UUID
    payment_id: int
    method: Literal["MEDIO_ORIGINAL", "EFECTIVO", "TRANSFERENCIA"]
    reason: str
    exchange_id: int | None = None
    return_id: int | None = None
    evidence_reference: str | None = None


class RefundEvidenceRequest(BaseModel):
    evidence_reference: str


class ExchangeChargeRequest(BaseModel):
    operation_uuid: UUID
