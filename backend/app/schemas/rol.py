from pydantic import BaseModel, ConfigDict


class RolResponse(BaseModel):
    id_rol: int
    nombre: str
    descripcion: str | None

    model_config = ConfigDict(from_attributes=True)
