from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ClienteResponse(BaseModel):
    id_cliente: int
    id_usuario: int
    fecha_registro: datetime
    estado: str

    model_config = ConfigDict(from_attributes=True)
