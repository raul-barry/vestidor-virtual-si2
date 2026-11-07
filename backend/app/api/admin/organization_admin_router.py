from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_platform_admin
from app.database.database import get_db
from app.models.usuario import Usuario
from app.schemas.organization_admin import (
    OrganizationAdminCreate,
    OrganizationBranchResponse,
    OrganizationCreate,
    OrganizationResponse,
    OrganizationStatus,
    OrganizationUpdate,
    OrganizationUserResponse,
    TenantProvisionRequest,
    TenantProvisionResponse,
)
from app.services.organization_admin_service import OrganizationAdminService
from app.services.tenant_provisioning_service import TenantProvisioningService
from app.api.subscription_router import _subscription_response


organization_admin_router = APIRouter(prefix="/platform/organizations", tags=["Administración de plataforma"])


@organization_admin_router.get("", response_model=list[OrganizationResponse])
def list_organizations(db: Session = Depends(get_db), _: Usuario = Depends(get_current_platform_admin)):
    return OrganizationAdminService(db).list_organizations()


@organization_admin_router.post("", status_code=201, response_model=OrganizationResponse)
def create_organization(data: OrganizationCreate, db: Session = Depends(get_db), _: Usuario = Depends(get_current_platform_admin)):
    return OrganizationAdminService(db).create_organization(data)


@organization_admin_router.post("/provision", status_code=201, response_model=TenantProvisionResponse)
def provision_organization(data: TenantProvisionRequest, db: Session = Depends(get_db), actor: Usuario = Depends(get_current_platform_admin)):
    result = TenantProvisioningService(db).provision(data, actor)
    return {"organization": result["organization"], "administrator": result["administrator"],
            "subscription": _subscription_response(result["subscription"])}


@organization_admin_router.get("/{organization_id}", response_model=OrganizationResponse)
def get_organization(organization_id: int, db: Session = Depends(get_db), _: Usuario = Depends(get_current_platform_admin)):
    return OrganizationAdminService(db).list_organization_detail(organization_id)


@organization_admin_router.patch("/{organization_id}", response_model=OrganizationResponse)
def update_organization(organization_id: int, data: OrganizationUpdate, db: Session = Depends(get_db), _: Usuario = Depends(get_current_platform_admin)):
    return OrganizationAdminService(db).update_organization(organization_id, data)


@organization_admin_router.patch("/{organization_id}/status", response_model=OrganizationResponse)
def set_organization_status(organization_id: int, data: OrganizationStatus, db: Session = Depends(get_db), _: Usuario = Depends(get_current_platform_admin)):
    return OrganizationAdminService(db).set_status(organization_id, data.estado)


@organization_admin_router.get("/{organization_id}/branches", response_model=list[OrganizationBranchResponse])
def list_organization_branches(organization_id: int, db: Session = Depends(get_db), _: Usuario = Depends(get_current_platform_admin)):
    return OrganizationAdminService(db).list_branches(organization_id)


@organization_admin_router.get("/{organization_id}/users", response_model=list[OrganizationUserResponse])
def list_organization_users(organization_id: int, db: Session = Depends(get_db), _: Usuario = Depends(get_current_platform_admin)):
    return OrganizationAdminService(db).list_users(organization_id)


@organization_admin_router.post("/{organization_id}/administrators", status_code=201)
def create_organization_admin(organization_id: int, data: OrganizationAdminCreate, db: Session = Depends(get_db), _: Usuario = Depends(get_current_platform_admin)):
    result = OrganizationAdminService(db).create_first_administrator(organization_id, data)
    return {"id_usuario": result["id_usuario"], "id_organizacion": organization_id,
            "correo": result["correo"], "rol": result["rol"]}
