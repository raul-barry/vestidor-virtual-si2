from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class CreatePaymentRequest(BaseModel):
    id_pedido: int
    metodo_pago: Literal["EFECTIVO", "QR", "TARJETA"]


PaymentState = Literal["PENDIENTE", "PROCESANDO", "PAGADO", "FALLIDO", "CANCELADO"]


class PaymentResponse(BaseModel):
    id_pago: int
    id_pedido: int
    metodo_pago: str
    monto: Decimal
    estado: PaymentState
    fecha_pago: datetime
    proveedor: str | None = None
    referencia_externa: str | None = None


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
