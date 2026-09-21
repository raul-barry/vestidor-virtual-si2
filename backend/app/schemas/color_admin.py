from pydantic import BaseModel, Field


class ColorResponse(BaseModel):
    id_color: int
    nombre: str


class CreateColorRequest(BaseModel):
    nombre: str = Field(min_length=1, max_length=50)
    estado: str | None = "ACTIVO"


class UpdateColorRequest(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=50)
    estado: str | None = None



class ColorAdminResponse(BaseModel):
    id_color: int
    nombre: str
    estado: str
