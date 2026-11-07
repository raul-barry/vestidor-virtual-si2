from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class AuditLogItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organizacion_id: int
    usuario_id: int | None
    rol: str
    accion: str
    entidad: str
    entidad_id: str | None
    fecha_hora: datetime
    resultado: str
    detalles: dict


class AuditLogPage(BaseModel):
    items: list[AuditLogItem]
    total: int
    limit: int
    offset: int
