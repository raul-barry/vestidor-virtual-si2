from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class OrderItemResponse(BaseModel):
    producto: str
    talla: str
    color: str
    cantidad: int
    precio_unitario: Decimal


class CreateOrderResponse(BaseModel):
    id_pedido: int
    estado: str
    total: Decimal


class OrderSummaryResponse(BaseModel):
    id_pedido: int
    fecha_pedido: datetime
    estado: str
    total: Decimal


class OrderDetailResponse(BaseModel):
    id_pedido: int
    fecha_pedido: datetime
    estado: str
    total: Decimal
    tipo_entrega: str | None = None
    detalles: list[OrderItemResponse]
