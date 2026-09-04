from decimal import Decimal

from pydantic import BaseModel, Field


class AddCartItemRequest(BaseModel):
    id_variante: int
    cantidad: int = Field(gt=0)


class UpdateCartItemRequest(BaseModel):
    cantidad: int = Field(gt=0)


class CartItemResponse(BaseModel):
    id_detalle: int
    producto: str
    talla: str
    color: str
    cantidad: int
    precio_unitario: Decimal


class CartResponse(BaseModel):
    id_carrito: int
    estado: str
    items: list[CartItemResponse]
    total: Decimal
