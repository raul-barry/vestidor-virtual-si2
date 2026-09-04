from decimal import Decimal

from pydantic import BaseModel


class CategoryResponse(BaseModel):
    id_categoria: int
    nombre: str


class VariantResponse(BaseModel):
    id_variante: int
    sku: str
    talla: str
    color: str


class ProductCatalogResponse(BaseModel):
    id_producto: int
    nombre: str
    descripcion: str | None
    precio_base: Decimal
    estado: str
    categoria: CategoryResponse
    variantes: list[VariantResponse]


class ProductVariantsResponse(BaseModel):
    id_producto: int
    nombre_producto: str
    tallas: list[str]
    colores: list[str]
    variantes: list[VariantResponse]


class BranchAvailabilityResponse(BaseModel):
    id_sucursal: int
    nombre_sucursal: str
    direccion: str
    stock_disponible: int


class AvailabilityResponse(BaseModel):
    id_producto: int
    nombre_producto: str
    disponibilidad: list[BranchAvailabilityResponse]
