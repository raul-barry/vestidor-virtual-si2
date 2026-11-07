from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import timezone


class SubscriptionAssignRequest(BaseModel):
    plan_id: int = Field(gt=0)
    fecha_fin: datetime | None = None

    @field_validator("fecha_fin")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("fecha_fin debe incluir zona horaria")
        return value.astimezone(timezone.utc) if value is not None else None

    @model_validator(mode="after")
    def require_future_end(self) -> "SubscriptionAssignRequest":
        if self.fecha_fin is not None and self.fecha_fin.astimezone(timezone.utc) <= datetime.now(timezone.utc):
            raise ValueError("fecha_fin debe ser posterior a la fecha actual")
        return self


class PlanFeatureResponse(BaseModel):
    id_plan_caracteristica: int
    codigo: str
    nombre: str
    descripcion: str | None
    habilitada: bool
    limite: int | None
    configuracion: dict | None


class AvailablePlanResponse(BaseModel):
    id_plan: int
    codigo: str
    nombre: str
    descripcion: str | None
    max_sucursales: int | None
    caracteristicas: list[PlanFeatureResponse]


class SubscriptionResponse(BaseModel):
    id_suscripcion: int
    organizacion_id: int
    plan_id: int
    plan_codigo: str
    plan_nombre: str
    estado: str
    fecha_inicio: datetime
    fecha_fin: datetime | None
    fecha_creacion: datetime
    fecha_actualizacion: datetime
    creado_por_id: int | None
