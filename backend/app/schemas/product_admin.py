from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CreateProductRequest(BaseModel):
    nombre: str = Field(min_length=1, max_length=150)
    descripcion: str | None = None
    precio_base: Decimal = Field(gt=0)
    id_categoria: int


class UpdateProductRequest(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=150)
    descripcion: str | None = None
    precio_base: Decimal | None = Field(default=None, gt=0)
    id_categoria: int | None = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def has_at_least_one_field(self) -> "UpdateProductRequest":
        if all(value is None for value in self.model_dump().values()):
            raise ValueError("Debe proporcionar al menos un campo para actualizar")
        return self


class AdminCategoryResponse(BaseModel):
    id_categoria: int
    nombre: str


class ProductAdminResponse(BaseModel):
    id_producto: int
    nombre: str
    descripcion: str | None
    precio_base: Decimal
    estado: str
    categoria: AdminCategoryResponse
    imagen_url: str | None = None
