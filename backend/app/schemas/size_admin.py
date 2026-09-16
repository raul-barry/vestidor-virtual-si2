from pydantic import BaseModel, Field


class SizeResponse(BaseModel):
    id_talla: int
    nombre: str


class CreateSizeRequest(BaseModel):
    nombre: str = Field(min_length=1, max_length=20)
    estado: str | None = "ACTIVO"


class UpdateSizeRequest(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=20)
    estado: str | None = None


class SizeAdminResponse(BaseModel):
    id_talla: int
    nombre: str
    estado: str
