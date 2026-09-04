from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProfileResponse(BaseModel):
    id_usuario: int
    nombres: str
    apellidos: str
    correo: str
    telefono: str | None


class ProfileUpdateRequest(BaseModel):
    nombres: str | None = Field(default=None, min_length=1, max_length=100)
    apellidos: str | None = Field(default=None, min_length=1, max_length=100)
    telefono: str | None = Field(default=None, min_length=1, max_length=30)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def has_at_least_one_field(self) -> "ProfileUpdateRequest":
        if self.nombres is None and self.apellidos is None and self.telefono is None:
            raise ValueError("Debe proporcionar al menos un campo para actualizar")
        return self
