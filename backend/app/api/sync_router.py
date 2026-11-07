import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import bearer_scheme, get_current_user
from app.database.database import get_db
from app.models.device_sync_credential import DeviceSyncCredential
from app.models.organizacion import Organizacion
from app.models.usuario import Usuario
from app.schemas.sync import SyncBatchInput
from app.services.sync_handlers import SyncActor
from app.services.sync_service import SyncService


sync_router = APIRouter(tags=["Sincronización offline"])


class DeviceCredentialInput(BaseModel):
    client_id: str = Field(min_length=1, max_length=100)


def get_sync_actor(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> SyncActor:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(401, "Credencial de sincronizaciÃ³n invÃ¡lida")
    token_hash = hashlib.sha256(credentials.credentials.encode("utf-8")).hexdigest()
    device = db.scalar(select(DeviceSyncCredential).where(
        DeviceSyncCredential.token_hash == token_hash,
        DeviceSyncCredential.revoked_at.is_(None),
    ))
    if device is None:
        user = get_current_user(credentials, db)
        return SyncActor(user.id_usuario, user.id_organizacion, user.rol.nombre)
    expires = device.expires_at if device.expires_at.tzinfo else device.expires_at.replace(tzinfo=timezone.utc)
    user = db.get(Usuario, device.usuario_id)
    organization = db.get(Organizacion, device.organizacion_id)
    if (expires <= datetime.now(timezone.utc) or user is None or organization is None
            or user.id_organizacion != device.organizacion_id
            or user.rol.nombre not in {"CLIENTE", "ADMINISTRADOR", "ENCARGADO_SUCURSAL", "CAJERO"}
            or user.estado.upper() != "ACTIVO" or organization.estado.upper() != "ACTIVA"):
        raise HTTPException(401, "Credencial de sincronizaciÃ³n expirada o revocada")
    db.info["organization_id"] = device.organizacion_id
    db.info["audit_actor_id"] = user.id_usuario
    db.info["audit_actor_role"] = user.rol.nombre
    return SyncActor(user.id_usuario, device.organizacion_id, user.rol.nombre,
                     device_limited=True, device_client_id=device.client_id,
                     device_credential_id=device.id)


@sync_router.post("/sync/device-credentials")
def issue_device_credential(request: DeviceCredentialInput,
                            db: Session = Depends(get_db),
                            user: Usuario = Depends(get_current_user)):
    if user.rol.nombre not in {"CLIENTE", "ADMINISTRADOR", "ENCARGADO_SUCURSAL", "CAJERO"}:
        raise HTTPException(403, "Solo clientes pueden emitir credenciales de sincronizaciÃ³n")
    token = "fssync_" + secrets.token_urlsafe(48)
    now = datetime.now(timezone.utc)
    row = DeviceSyncCredential(
        organizacion_id=user.id_organizacion, usuario_id=user.id_usuario,
        client_id=request.client_id,
        token_hash=hashlib.sha256(token.encode("utf-8")).hexdigest(),
        expires_at=now + timedelta(days=30), created_at=now,
    )
    db.add(row)
    db.commit()
    return {"credential_id": row.id, "sync_token": token, "expires_at": row.expires_at}


@sync_router.delete("/sync/device-credentials/{credential_id}")
def revoke_device_credential(credential_id: int, db: Session = Depends(get_db),
                             user: Usuario = Depends(get_current_user)):
    row = db.scalar(select(DeviceSyncCredential).where(
        DeviceSyncCredential.id == credential_id,
        DeviceSyncCredential.organizacion_id == user.id_organizacion,
        DeviceSyncCredential.usuario_id == user.id_usuario,
    ).with_for_update())
    if row is None:
        raise HTTPException(404, "Credencial de dispositivo no encontrada")
    row.revoked_at = datetime.now(timezone.utc)
    db.commit()
    return {"revoked": True, "credential_id": row.id}


@sync_router.post("/sync/batch")
def sync_batch(
    request: SyncBatchInput,
    db: Session = Depends(get_db),
    actor: SyncActor = Depends(get_sync_actor),
):
    response = SyncService.process(db, actor, request)
    db.commit()
    statuses = [item.http_status for item in response.results]
    http_status = 403 if 403 in statuses else 409 if 409 in statuses else 200
    return JSONResponse(status_code=http_status, content=response.model_dump(mode="json"))
