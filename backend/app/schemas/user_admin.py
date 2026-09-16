from typing import Literal

from pydantic import BaseModel, Field


class UserAdminResponse(BaseModel):
    id_usuario: int
    nombres: str
    apellidos: str
    correo: str
    telefono: str | None
    estado: str
    rol: str


class CreateUserAdminRequest(BaseModel):
    nombres: str = Field(min_length=1, max_length=100)
    apellidos: str = Field(min_length=1, max_length=100)
    correo: str = Field(min_length=1, max_length=255)
    telefono: str | None = Field(default=None, max_length=30)
    password: str = Field(min_length=8)
    rol: str = Field(min_length=1, max_length=100)
    id_sucursal: int | None = None


class UpdateStatusRequest(BaseModel):
    estado: Literal["ACTIVO", "INACTIVO"]


class UpdateRoleRequest(BaseModel):
    id_rol: int
