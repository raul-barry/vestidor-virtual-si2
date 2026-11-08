from pydantic import BaseModel, ConfigDict, Field, model_validator


class PlanAdminUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    descripcion: str | None = None
    max_sucursales: int | None = Field(default=None, gt=0)
    activo: bool | None = None

    @model_validator(mode="after")
    def at_least_one_field(self):
        if not self.model_fields_set:
            raise ValueError("Debe enviar al menos un campo para actualizar")
        return self


class PlanFeatureAdminUpdate(BaseModel):
    codigo: str = Field(min_length=1, max_length=80)
    habilitada: bool | None = None
    limite: int | None = Field(default=None, ge=0)
    configuracion: dict | None = None

    @model_validator(mode="after")
    def validate_fields(self):
        if not ({"habilitada", "limite", "configuracion"} & self.model_fields_set):
            raise ValueError("Debe indicar habilitada, limite o configuracion")
        return self


class PlanFeaturesAdminUpdate(BaseModel):
    caracteristicas: list[PlanFeatureAdminUpdate]

    @model_validator(mode="after")
    def unique_codes(self):
        codes = ["reportes_ia" if item.codigo == "reportes_gemini" else item.codigo
                 for item in self.caracteristicas]
        if len(codes) != len(set(codes)):
            raise ValueError("No se permiten códigos de característica duplicados")
        return self


class PlanFeatureAdminResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id_plan_caracteristica: int
    codigo: str
    nombre: str
    descripcion: str | None
    habilitada: bool
    limite: int | None
    configuracion: dict | None


class PlanAdminResponse(BaseModel):
    id_plan: int
    codigo: str
    nombre: str
    descripcion: str | None
    max_sucursales: int | None
    activo: bool
    caracteristicas: list[PlanFeatureAdminResponse]
