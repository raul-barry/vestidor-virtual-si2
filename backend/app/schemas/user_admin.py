from typing import Literal

from pydantic import BaseModel


class UserAdminResponse(BaseModel):
    id_usuario: int
    nombres: str
    apellidos: str
    correo: str
    telefono: str | None
    estado: str
    rol: str


class UpdateStatusRequest(BaseModel):
    estado: Literal["ACTIVO", "INACTIVO"]


class UpdateRoleRequest(BaseModel):
    id_rol: int
