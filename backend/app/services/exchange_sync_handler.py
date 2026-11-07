from fastapi import HTTPException

from app.models.exchange import GarmentExchange
from app.models.usuario import Usuario
from app.services.exchange_service import create_customer_request, exchange_record, register_offline_physical_exchange
from app.services.sync_handlers import SyncActor, SyncHandlerError, SyncHandlerRegistry


def _handle_http_error(error: HTTPException) -> SyncHandlerError:
    category = "DATOS_INVALIDOS" if error.status_code in (400, 422) else (
        "NO_AUTORIZADA" if error.status_code in (401, 403, 404) else "CONFLICTO_ESTADO"
    )
    return SyncHandlerError(str(error.detail), category, result={"http_status": error.status_code})


def request_exchange(db, actor: SyncActor, payload: dict):
    if actor.role != "CLIENTE":
        raise SyncHandlerError("La solicitud de cambio requiere una sesión de cliente.", "NO_AUTORIZADA")
    if payload.get("id_usuario") != actor.user_id:
        raise SyncHandlerError("La solicitud no pertenece al usuario autenticado.", "NO_AUTORIZADA")
    try:
        row = create_customer_request(
            db, organization_id=actor.organization_id, customer_user_id=actor.user_id,
            detail_id=int(payload["id_detalle"]), branch_id=int(payload["id_sucursal"]),
            replacement_variant_id=int(payload["id_variante_sustituta"]) if payload.get("id_variante_sustituta") is not None else None,
            reason=str(payload.get("motivo", "Solicitud de cambio offline"))[:255],
            operation_uuid=str(payload.get("_operation_uuid") or ""),
        )
        return exchange_record(db, row)
    except HTTPException as error:
        raise _handle_http_error(error) from error


def register_physical_exchange(db, actor: SyncActor, payload: dict):
    if actor.role not in {"ADMINISTRADOR", "ENCARGADO_SUCURSAL"}:
        raise SyncHandlerError("Solo el personal autorizado puede registrar entregas físicas.", "NO_AUTORIZADA")
    if payload.get("id_usuario") != actor.user_id:
        raise SyncHandlerError("La operación física no pertenece al empleado autenticado.", "NO_AUTORIZADA")
    try:
        employee = db.get(Usuario, actor.user_id)
        if employee is None:
            raise SyncHandlerError("Empleado no encontrado en la organización.", "NO_AUTORIZADA")
        payload = {**payload, "operation_uuid": payload.get("_operation_uuid")}
        result = register_offline_physical_exchange(db, organization_id=actor.organization_id,
                                                    employee=employee, payload=payload)
        return result
    except HTTPException as error:
        raise _handle_http_error(error) from error


def register_exchange_handlers(registry: SyncHandlerRegistry) -> None:
    registry.register("cambio.solicitar", request_exchange)
    registry.register("cambio.registrar_offline", register_physical_exchange)
