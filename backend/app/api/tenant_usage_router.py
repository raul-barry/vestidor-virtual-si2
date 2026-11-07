from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_platform_admin, require_roles
from app.database.database import get_db
from app.models.usuario import Usuario
from app.schemas.tenant_usage import TenantUsageResponse
from app.services.tenant_usage_service import TenantUsageService

tenant_usage_router = APIRouter(tags=["Consumo SaaS"])


@tenant_usage_router.get(
    "/platform/organizations/{organization_id}/usage",
    response_model=TenantUsageResponse,
)
def get_platform_organization_usage(
    organization_id: int,
    desde: date | None = Query(default=None),
    hasta: date | None = Query(default=None),
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_platform_admin),
):
    return TenantUsageService(db).get_usage(organization_id, desde, hasta)


@tenant_usage_router.get("/organizations/me/usage", response_model=TenantUsageResponse)
def get_my_organization_usage(
    desde: date | None = Query(default=None),
    hasta: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMINISTRADOR")),
):
    return TenantUsageService(db).get_usage(current_user.id_organizacion, desde, hasta)
