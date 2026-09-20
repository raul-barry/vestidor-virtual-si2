from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class CreatePaymentRequest(BaseModel):
    id_pedido: int
    metodo_pago: Literal["EFECTIVO", "QR", "TARJETA"]


class PaymentResponse(BaseModel):
    id_pago: int
    id_pedido: int
    metodo_pago: str
    monto: Decimal
    estado: str
    fecha_pago: datetime
    proveedor: str | None = None
    referencia_externa: str | None = None


class StripeIntentRequest(BaseModel):
    id_pedido: int


class StripeIntentResponse(BaseModel):
    client_secret: str
    publishable_key: str
    payment: PaymentResponse


class PaymentStatusResponse(BaseModel):
    payment: PaymentResponse
    order_status: str
