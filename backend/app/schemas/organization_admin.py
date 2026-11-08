from typing import Any
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, field_validator, model_validator
from app.schemas.subscription import SubscriptionAssignRequest, SubscriptionResponse


EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
NIT_PATTERN = r"^[A-Z0-9]+(?:-[A-Z0-9]+)*$"
PHONE_PATTERN = r"^[+0-9() .-]{6,30}$"
SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


def _clean_optional(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


class OrganizationCreate(BaseModel):
    nombre: str = Field(min_length=2, max_length=150)
    razon_social: str | None = Field(default=None, max_length=200)
    nit: str | None = Field(default=None, min_length=3, max_length=20, pattern=NIT_PATTERN)
    correo_contacto: str | None = Field(default=None, max_length=254, pattern=EMAIL_PATTERN)
    telefono_contacto: str | None = Field(default=None, min_length=6, max_length=30, pattern=PHONE_PATTERN)
    direccion: str | None = Field(default=None, max_length=255)
    logo_url: str | None = Field(default=None, max_length=2048)
    slug: str | None = Field(default=None, min_length=2, max_length=160, pattern=SLUG_PATTERN)

    @field_validator("nombre", "razon_social", "direccion", mode="before")
    @classmethod
    def trim_names_and_address(cls, value: Any) -> Any:
        return _clean_optional(value)

    @field_validator("nit", mode="before")
    @classmethod
    def normalize_nit(cls, value: Any) -> Any:
        value = _clean_optional(value)
        return value.upper() if isinstance(value, str) else value

    @field_validator("correo_contacto", mode="before")
    @classmethod
    def normalize_contact_email(cls, value: Any) -> Any:
        value = _clean_optional(value)
        return value.lower() if isinstance(value, str) else value

    @field_validator("slug", mode="before")
    @classmethod
    def normalize_slug(cls, value: Any) -> Any:
        value = _clean_optional(value)
        return value.lower() if isinstance(value, str) else value

    @field_validator("logo_url")
    @classmethod
    def validate_logo_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parsed = urlsplit(value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("logo_url debe ser una URL http o https válida")
        return value


class OrganizationUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=150)
    razon_social: str | None = Field(default=None, max_length=200)
    nit: str | None = Field(default=None, min_length=3, max_length=20, pattern=NIT_PATTERN)
    correo_contacto: str | None = Field(default=None, max_length=254, pattern=EMAIL_PATTERN)
    telefono_contacto: str | None = Field(default=None, min_length=6, max_length=30, pattern=PHONE_PATTERN)
    direccion: str | None = Field(default=None, max_length=255)
    logo_url: str | None = Field(default=None, max_length=2048)
    slug: str | None = Field(default=None, min_length=2, max_length=160, pattern=SLUG_PATTERN)

    @model_validator(mode="after")
    def validate_patch(self) -> "OrganizationUpdate":
        if not self.model_fields_set:
            raise ValueError("Debe especificar al menos un campo para actualizar")
        for field in ("nombre", "slug"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} no se puede borrar")
        return self

    @field_validator("nombre", "razon_social", "direccion", mode="before")
    @classmethod
    def trim_names_and_address(cls, value: Any) -> Any:
        return _clean_optional(value)

    @field_validator("nit", mode="before")
    @classmethod
    def normalize_nit(cls, value: Any) -> Any:
        value = _clean_optional(value)
        return value.upper() if isinstance(value, str) else value

    @field_validator("correo_contacto", mode="before")
    @classmethod
    def normalize_contact_email(cls, value: Any) -> Any:
        value = _clean_optional(value)
        return value.lower() if isinstance(value, str) else value

    @field_validator("slug", mode="before")
    @classmethod
    def normalize_slug(cls, value: Any) -> Any:
        value = _clean_optional(value)
        return value.lower() if isinstance(value, str) else value

    @field_validator("logo_url", mode="before")
    @classmethod
    def validate_logo_url(cls, value: Any) -> str | None:
        value = _clean_optional(value)
        if value is None:
            return None
        parsed = urlsplit(value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("logo_url debe ser una URL http o https válida")
        return value


class OrganizationResponse(BaseModel):
    id_organizacion: int
    nombre: str
    razon_social: str | None
    nit: str | None
    correo_contacto: str | None
    telefono_contacto: str | None
    direccion: str | None
    logo_url: str | None
    slug: str
    estado: str
    fecha_creacion: str | None
    fecha_actualizacion: str | None


class OrganizationBranchResponse(BaseModel):
    id_sucursal: int
    nombre: str
    direccion: str
    ciudad: str
    estado: str


class OrganizationUserResponse(BaseModel):
    id_usuario: int
    nombre: str
    correo: str
    rol: str
    estado: str
    fecha_registro: str


class OrganizationStatus(BaseModel):
    estado: str = Field(pattern="^(ACTIVA|INACTIVA)$")


class OrganizationAdminCreate(BaseModel):
    nombres: str = Field(min_length=1, max_length=100)
    apellidos: str = Field(min_length=1, max_length=100)
    correo: str = Field(min_length=3, max_length=255, pattern=EMAIL_PATTERN)
    telefono: str | None = Field(default=None, max_length=30, pattern=PHONE_PATTERN)
    password: str = Field(min_length=12, max_length=128)

    @field_validator("correo", mode="before")
    @classmethod
    def normalize_admin_email(cls, value: Any) -> Any:
        value = _clean_optional(value)
        return value.lower() if isinstance(value, str) else value

    @field_validator("nombres", "apellidos", mode="before")
    @classmethod
    def trim_admin_names(cls, value: Any) -> Any:
        return _clean_optional(value)

    @field_validator("telefono", mode="before")
    @classmethod
    def clean_admin_phone(cls, value: Any) -> Any:
        return _clean_optional(value)


class TenantProvisionRequest(BaseModel):
    organization: OrganizationCreate
    administrator: OrganizationAdminCreate
    subscription: SubscriptionAssignRequest


class TenantProvisionResponse(BaseModel):
    organization: OrganizationResponse
    administrator: dict
    subscription: SubscriptionResponse
