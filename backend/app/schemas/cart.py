from decimal import Decimal

from pydantic import BaseModel, Field


class AddCartItemRequest(BaseModel):
    id_variante: int
    cantidad: int = Field(gt=0)
    id_reserva: int | None = Field(default=None, gt=0)


class UpdateCartItemRequest(BaseModel):
    cantidad: int = Field(gt=0)


class CartItemResponse(BaseModel):
    id_detalle: int
    id_variante: int
    producto: str
    talla: str
    color: str
    cantidad: int
    precio_unitario: Decimal
    id_reserva: int | None = None


class CartResponse(BaseModel):
    id_carrito: int
    estado: str
    items: list[CartItemResponse]
    total: Decimal
