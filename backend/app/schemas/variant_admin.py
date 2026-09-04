from pydantic import BaseModel, ConfigDict, Field, model_validator


class CreateVariantRequest(BaseModel):
    sku: str = Field(min_length=1, max_length=100)
    id_talla: int
    id_color: int


class UpdateVariantRequest(BaseModel):
    sku: str | None = Field(default=None, min_length=1, max_length=100)
    id_talla: int | None = None
    id_color: int | None = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def has_at_least_one_field(self) -> "UpdateVariantRequest":
        if all(value is None for value in self.model_dump().values()):
            raise ValueError("Debe proporcionar al menos un campo para actualizar")
        return self


class VariantAdminResponse(BaseModel):
    id_variante: int
    sku: str
    producto: str
    talla: str
    color: str
    estado: str
