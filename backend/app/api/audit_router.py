from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_platform_admin, require_roles
from app.database.database import get_db
from app.models.usuario import Usuario
from app.models.organizacion import Organizacion
from app.schemas.audit_log import AuditLogPage
from app.services.audit_service import AuditService

audit_router = APIRouter(tags=["Auditoría empresarial"])


def _page(db, organization_id, desde, hasta, tipo, usuario_id, limit, offset):
    if db.get(Organizacion, organization_id) is None:
        raise HTTPException(404, "Organización no encontrada")
    if desde and desde.tzinfo is None: desde = desde.replace(tzinfo=timezone.utc)
    if hasta and hasta.tzinfo is None: hasta = hasta.replace(tzinfo=timezone.utc)
    if desde and hasta and desde > hasta: raise HTTPException(422, "desde no puede ser posterior a hasta")
    total, rows = AuditService.list_activity(db, organization_id, desde=desde, hasta=hasta, tipo=tipo, usuario_id=usuario_id, limit=limit, offset=offset)
    return AuditLogPage(items=rows, total=total, limit=limit, offset=offset)


@audit_router.get("/platform/organizations/{organization_id}/activity", response_model=AuditLogPage)
def platform_activity(organization_id: int, desde: datetime | None = None, hasta: datetime | None = None,
                      tipo: str | None = None, usuario_id: int | None = None,
                      limit: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0),
                      db: Session = Depends(get_db), _: Usuario = Depends(get_current_platform_admin)):
    return _page(db, organization_id, desde, hasta, tipo, usuario_id, limit, offset)


@audit_router.get("/organizations/me/activity", response_model=AuditLogPage)
def own_activity(desde: datetime | None = None, hasta: datetime | None = None,
                 tipo: str | None = None, usuario_id: int | None = None,
                 limit: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0),
                 db: Session = Depends(get_db), user: Usuario = Depends(require_roles("ADMINISTRADOR"))):
    return _page(db, user.id_organizacion, desde, hasta, tipo, usuario_id, limit, offset)
