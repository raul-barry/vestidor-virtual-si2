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
