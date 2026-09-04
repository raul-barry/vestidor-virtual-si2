from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class InventoryResponse(BaseModel):
    id_inventario: int
    producto: str
    sku: str
    talla: str
    color: str
    sucursal: str
    stock: int
    stock_bajo: bool


class CreateInventoryRequest(BaseModel):
    id_variante: int
    id_sucursal: int
    stock: int = Field(ge=0)


class StockMovementRequest(BaseModel):
    tipo_movimiento: Literal["ENTRADA", "SALIDA", "AJUSTE"] | None = None
    cantidad: int = Field(gt=0)
    motivo: str = Field(min_length=1, max_length=255)


class StockAdjustmentRequest(BaseModel):
    nuevo_stock: int = Field(ge=0)
    motivo: str = Field(min_length=1, max_length=255)


class InventoryMovementResponse(BaseModel):
    tipo: str
    cantidad: int
    stock_anterior: int
    stock_nuevo: int
    fecha: datetime
    usuario: str
