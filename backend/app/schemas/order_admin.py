from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class OrderAdminResponse(BaseModel):
    id_pedido: int
    cliente: str
    fecha: datetime
    estado: str
    total: Decimal


class OrderAdminItemResponse(BaseModel):
    producto: str
    talla: str
    color: str
    cantidad: int
    precio_unitario: Decimal


class OrderPaymentResponse(BaseModel):
    id_pago: int
    metodo_pago: str
    monto: Decimal
    estado: str


class OrderAdminDetailResponse(OrderAdminResponse):
    detalles: list[OrderAdminItemResponse]
    pago: OrderPaymentResponse | None


class UpdateOrderStatusRequest(BaseModel):
    estado: Literal["PENDIENTE", "CONFIRMADO", "PREPARANDO", "ENVIADO", "ENTREGADO", "CANCELADO"]
