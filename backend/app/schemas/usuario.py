from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.rol import RolResponse


class UsuarioCreate(BaseModel):
    nombres: str = Field(min_length=1, max_length=100)
    apellidos: str = Field(min_length=1, max_length=100)
    correo: str = Field(min_length=1, max_length=255)
    telefono: str | None = Field(default=None, max_length=30)
    password: str = Field(min_length=8)


class UsuarioResponse(BaseModel):
    id_usuario: int
    id_rol: int
    nombres: str
    apellidos: str
    correo: str
    telefono: str | None
    estado: str
    fecha_registro: datetime
    rol: RolResponse | None = None

    model_config = ConfigDict(from_attributes=True)
