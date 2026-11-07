from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.organizacion import Organizacion
from app.models.plan import Plan
from app.models.usuario import Usuario
from app.schemas.organization_admin import TenantProvisionRequest
from app.services.audit_service import AuditService
from app.services.organization_admin_service import OrganizationAdminService, _slugify
from app.services.subscription_service import SubscriptionService


class TenantProvisioningService:
    """Coordinates existing organization, administrator, and subscription services atomically."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def provision(self, request: TenantProvisionRequest, actor: Usuario) -> dict:
        if actor.rol.nombre != "ADMINISTRADOR_PLATAFORMA":
            raise AppException("Solo el administrador de plataforma puede aprovisionar empresas", status_code=403)
        self.db.info.pop("organization_id", None)
        self.db.info["audit_actor_id"] = actor.id_usuario
        self.db.info["audit_actor_role"] = actor.rol.nombre
        organization_data = request.organization.model_dump()
        target_slug = organization_data.get("slug") or _slugify(organization_data["nombre"].strip())
        if self.db.scalar(select(Organizacion.id_organizacion).where(Organizacion.slug == target_slug)):
            raise AppException("El slug de empresa ya está registrado", status_code=409)
        nit = organization_data.get("nit")
        if nit and self.db.scalar(select(Organizacion.id_organizacion).where(Organizacion.nit == nit)):
            raise AppException("El NIT de empresa ya está registrado", status_code=409)
        if self.db.scalar(select(Usuario.id_usuario).where(func.lower(Usuario.correo) == request.administrator.correo.lower())):
            raise AppException("El correo de administrador ya está registrado", status_code=409)
        plan_service = SubscriptionService(self.db)
        plan = self.db.get(Plan, request.subscription.plan_id)
        if plan is None or not plan.activo:
            raise AppException("Plan no encontrado o inactivo", status_code=404)

        organizations = OrganizationAdminService(self.db)
        try:
            organization = organizations.create_organization(request.organization, commit=False)
            organization_id = organization["id_organizacion"]
            AuditService.record(
                self.db, organization_id=organization_id, actor_id=actor.id_usuario,
                actor_role=actor.rol.nombre, action="ORGANIZACION_CREADA",
                entity="Organizacion", entity_id=organization_id,
                details={"campos": sorted(key for key, value in organization_data.items() if value is not None)},
            )
            administrator = organizations.create_first_administrator(
                organization_id, request.administrator, commit=False
            )
            subscription = plan_service.assign(
                organization_id, request.subscription.plan_id, actor.id_usuario,
                request.subscription.fecha_fin, commit=False,
            )
            self.db.commit()
            return {"organization": organization, "administrator": administrator, "subscription": subscription}
        except IntegrityError as exc:
            self.db.rollback()
            raise AppException("El aprovisionamiento no pudo completarse por un dato duplicado o una relación inválida", status_code=409) from exc
        except Exception:
            self.db.rollback()
            raise
