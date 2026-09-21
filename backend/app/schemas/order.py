from datetime import datetime
from decimal import Decimal

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class CreateOrderRequest(BaseModel):
    # Optional only for backwards-compatible clients that still send an empty
    # object. New checkout requests always provide a delivery mode.
    tipo_entrega: Literal["RECOJO_SUCURSAL", "DELIVERY"] | None = None
    id_sucursal_entrega: int | None = Field(default=None, gt=0)
    direccion_entrega: str | None = Field(default=None, min_length=3, max_length=255)
    referencia_entrega: str | None = Field(default=None, max_length=255)
    telefono_entrega: str | None = Field(default=None, min_length=6, max_length=30)

    @model_validator(mode="after")
    def validate_delivery_details(self):
        if self.tipo_entrega is None:
            if any((self.id_sucursal_entrega, self.direccion_entrega, self.referencia_entrega, self.telefono_entrega)):
                raise ValueError("Indique el tipo de entrega")
            return self
        if self.tipo_entrega == "RECOJO_SUCURSAL":
            if self.id_sucursal_entrega is None:
                raise ValueError("Seleccione una sucursal de recojo")
            return self
        if not self.direccion_entrega or not self.telefono_entrega:
            raise ValueError("Delivery requiere dirección y teléfono")
        return self


class DeliveryBranchResponse(BaseModel):
    id_sucursal: int
    nombre: str
    direccion: str


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
    id_sucursal_entrega: int | None = None
    direccion_entrega: str | None = None
    referencia_entrega: str | None = None
    telefono_entrega: str | None = None
    detalles: list[OrderItemResponse]
