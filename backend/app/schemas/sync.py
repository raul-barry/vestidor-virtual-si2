from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SyncStatus(StrEnum):
    SINCRONIZADA = "SINCRONIZADA"
    RECHAZADA = "RECHAZADA"
    ERROR_REINTENTABLE = "ERROR_REINTENTABLE"


class SyncCategory(StrEnum):
    TEMPORAL = "TEMPORAL"
    DUPLICADA = "DUPLICADA"
    DATOS_INVALIDOS = "DATOS_INVALIDOS"
    CONFLICTO_INVENTARIO = "CONFLICTO_INVENTARIO"
    CONFLICTO_ESTADO = "CONFLICTO_ESTADO"
    NO_AUTORIZADA = "NO_AUTORIZADA"
    OPERACION_NO_IMPLEMENTADA = "OPERACION_NO_IMPLEMENTADA"
    UUID_REUTILIZADO = "UUID_REUTILIZADO"


class SyncOperationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation_uuid: UUID
    operation_type: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z][A-Za-z0-9_.-]*$")
    payload: dict[str, Any]
    created_at: datetime
    schema_version: int = Field(ge=1, le=1000)
    client_id: str = Field(min_length=1, max_length=100)
    tenant_scope: str = Field(min_length=1, max_length=180)


class SyncBatchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operations: list[SyncOperationInput] = Field(min_length=1, max_length=100)


class SyncOperationResult(BaseModel):
    operation_uuid: UUID
    status: SyncStatus
    category: SyncCategory | None = None
    message: str | None = None
    duplicate: bool = False
    result: dict[str, Any] = Field(default_factory=dict)
    http_status: int = 200


class SyncBatchOutput(BaseModel):
    results: list[SyncOperationResult]
    processed_at: datetime
