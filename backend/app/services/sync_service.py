import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.sync_idempotency import SyncIdempotency
from app.services.audit_service import AuditService
from app.schemas.sync import (
    SyncBatchInput, SyncBatchOutput, SyncCategory, SyncOperationResult, SyncStatus,
)
from app.services.sync_handlers import SyncActor, SyncHandlerError, sync_handlers


def _digest(operation) -> str:
    content = operation.model_dump(mode="json", exclude={"operation_uuid"})
    canonical = json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class SyncService:
    @staticmethod
    def process(db: Session, actor: SyncActor, batch: SyncBatchInput) -> SyncBatchOutput:
        results: list[SyncOperationResult] = []
        expected_scope = f"org:{actor.organization_id}"
        for operation in batch.operations:
            operation_uuid = str(operation.operation_uuid)
            permitted_device_operations = (
                {"reserva.crear", "reserva.cancelar", "venta.crear", "cambio.solicitar", "pago.solicitar"}
                if actor.role == "CLIENTE" else
                {"pos.venta_contado"} if actor.role in {"CAJERO", "ADMINISTRADOR"} else
                {"cambio.registrar_offline"}
            )
            if actor.device_limited and (
                operation.operation_type not in permitted_device_operations
                or operation.client_id != actor.device_client_id
            ):
                results.append(SyncOperationResult(
                    operation_uuid=operation.operation_uuid, status=SyncStatus.RECHAZADA,
                    category=SyncCategory.NO_AUTORIZADA,
                    message="La credencial de dispositivo no autoriza este tipo de operación.",
                    http_status=403,
                ))
                continue
            if operation.tenant_scope != expected_scope:
                results.append(SyncOperationResult(
                    operation_uuid=operation.operation_uuid, status=SyncStatus.RECHAZADA,
                    category=SyncCategory.NO_AUTORIZADA,
                    message="El scope local no coincide con la organización de la sesión.", http_status=403,
                ))
                continue

            fingerprint = _digest(operation)
            existing = db.scalar(select(SyncIdempotency).where(
                SyncIdempotency.organizacion_id == actor.organization_id,
                SyncIdempotency.operation_uuid == operation_uuid,
            ).with_for_update())
            if existing is not None:
                if existing.payload_hash != fingerprint:
                    results.append(SyncOperationResult(
                        operation_uuid=operation.operation_uuid, status=SyncStatus.RECHAZADA,
                        category=SyncCategory.UUID_REUTILIZADO,
                        message="El UUID ya fue usado con contenido diferente.", http_status=409,
                    ))
                    continue
                if existing.status != SyncStatus.ERROR_REINTENTABLE.value:
                    prior = dict(existing.result_json)
                    prior["duplicate"] = True
                    results.append(SyncOperationResult.model_validate(prior))
                    continue
                result = SyncService._execute(db, actor, operation)
                SyncService._save_result(existing, result)
                SyncService._audit(db, actor, operation_uuid, operation.operation_type, operation.client_id, result)
                results.append(result)
                continue

            row = SyncIdempotency(
                organizacion_id=actor.organization_id,
                operation_uuid=operation_uuid,
                operation_type=operation.operation_type,
                payload_hash=fingerprint,
                client_id=operation.client_id,
                tenant_scope=expected_scope,
                schema_version=operation.schema_version,
                operation_created_at=operation.created_at,
                status="ENVIANDO",
                result_json={"operation_uuid": operation_uuid, "status": "ENVIANDO"},
            )
            try:
                with db.begin_nested():
                    db.add(row)
                    db.flush([row])
            except IntegrityError:
                winner = db.scalar(select(SyncIdempotency).where(
                    SyncIdempotency.organizacion_id == actor.organization_id,
                    SyncIdempotency.operation_uuid == operation_uuid,
                ))
                if winner is None:
                    raise
                if winner.payload_hash != fingerprint:
                    results.append(SyncOperationResult(
                        operation_uuid=operation.operation_uuid, status=SyncStatus.RECHAZADA,
                        category=SyncCategory.UUID_REUTILIZADO,
                        message="El UUID ya fue usado con contenido diferente.", http_status=409,
                    ))
                else:
                    prior = dict(winner.result_json)
                    prior["duplicate"] = True
                    results.append(SyncOperationResult.model_validate(prior))
            else:
                result = SyncService._execute(db, actor, operation)
                SyncService._save_result(row, result)
                SyncService._audit(db, actor, operation_uuid, operation.operation_type, operation.client_id, result)
                results.append(result)
        return SyncBatchOutput(results=results, processed_at=datetime.now(timezone.utc))

    @staticmethod
    def _execute(db: Session, actor: SyncActor, operation) -> SyncOperationResult:
        handler = sync_handlers.get(operation.operation_type)
        if handler is None:
            return SyncOperationResult(
                operation_uuid=operation.operation_uuid, status=SyncStatus.RECHAZADA,
                category=SyncCategory.OPERACION_NO_IMPLEMENTADA,
                message="No hay un handler habilitado para esta operación.",
            )
        try:
            with db.begin_nested():
                payload = dict(operation.payload)
                if operation.operation_type.startswith("cambio.") or operation.operation_type == "pago.solicitar":
                    payload["_operation_uuid"] = str(operation.operation_uuid)
                data = handler(db, actor, payload)
            return SyncOperationResult(
                operation_uuid=operation.operation_uuid, status=SyncStatus.SINCRONIZADA,
                result=data or {},
            )
        except SyncHandlerError as error:
            return SyncOperationResult(
                operation_uuid=operation.operation_uuid,
                status=SyncStatus.ERROR_REINTENTABLE if error.retryable else SyncStatus.RECHAZADA,
                category=SyncCategory(error.category), message=str(error),
                result=error.result,
            )

    @staticmethod
    def _save_result(row: SyncIdempotency, result: SyncOperationResult) -> None:
        row.status = result.status.value
        row.result_json = result.model_dump(mode="json")
        row.error_code = result.category.value if result.category else None
        row.error_message = result.message
        row.updated_at = datetime.now(timezone.utc)

    @staticmethod
    def _audit(db: Session, actor: SyncActor, operation_uuid: str, operation_type: str, client_id: str,
               result: SyncOperationResult) -> None:
        AuditService.record(
            db, organization_id=actor.organization_id, actor_id=actor.user_id,
            actor_role=actor.role, action="OPERACION_SINCRONIZACION_PROCESADA",
            entity="OperacionOffline", entity_id=operation_uuid,
            result=result.status.value,
            details={"operation_type": operation_type, "client_id": client_id,
                     "category": result.category.value if result.category else None,
                     "result": result.result},
            dedupe_key=f"sync:{actor.organization_id}:{operation_uuid}:{result.status.value}",
        )
