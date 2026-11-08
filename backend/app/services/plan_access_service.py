from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Depends, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.security import get_current_user
from app.database.database import get_db
from app.models.organizacion import Organizacion
from app.models.plan import PlanCaracteristica
from app.models.suscripcion import Suscripcion
from app.models.sucursal import Sucursal
from app.models.usuario import Usuario
from app.services.subscription_service import SubscriptionService


@dataclass(frozen=True)
class PlanAccess:
    organization_id: int
    has_subscription_history: bool
    subscription: Suscripcion | None = None

    @property
    def plan(self):
        return self.subscription.plan if self.subscription is not None else None


class PlanAccessService:
    """Resolve plan rights from the authenticated database tenant context."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def resolve(self, *, lock_organization: bool = False, commit_expiration: bool = True) -> PlanAccess:
        organization_id = self.db.info.get("organization_id")
        if not isinstance(organization_id, int):
            raise HTTPException(403, detail={
                "code": "TENANT_CONTEXT_REQUIRED",
                "message": "No se pudo determinar la organización autenticada.",
            })

        organization_query = select(Organizacion).where(Organizacion.id_organizacion == organization_id)
        if lock_organization:
            organization_query = organization_query.with_for_update()
        if self.db.scalar(organization_query) is None:
            raise HTTPException(404, detail={"code": "ORGANIZATION_NOT_FOUND", "message": "Organización no encontrada."})

        now = datetime.now(timezone.utc)
        SubscriptionService(self.db).expire_due(
            organization_id, now=now, commit=commit_expiration
        )

        history_exists = self.db.scalar(
            select(Suscripcion.id_suscripcion)
            .where(Suscripcion.organizacion_id == organization_id)
            .limit(1)
        ) is not None
        if not history_exists:
            # Compatibility window for tenants provisioned before subscriptions.
            return PlanAccess(organization_id=organization_id, has_subscription_history=False)

        current = self.db.scalar(
            select(Suscripcion)
            .options(joinedload(Suscripcion.plan))
            .where(
                Suscripcion.organizacion_id == organization_id,
                Suscripcion.estado == "ACTIVA",
                Suscripcion.fecha_inicio <= now,
                or_(Suscripcion.fecha_fin.is_(None), Suscripcion.fecha_fin > now),
            )
            .order_by(Suscripcion.fecha_inicio.desc(), Suscripcion.id_suscripcion.desc())
        )
        return PlanAccess(
            organization_id=organization_id,
            has_subscription_history=True,
            subscription=current,
        )

    def require_branch_capacity(self) -> None:
        # If expiry is detected this request will be denied, so committing the
        # state transition is safe even though it releases the organization lock.
        # A valid subscription causes no commit and keeps the lock through branch insert.
        access = self.resolve(lock_organization=True, commit_expiration=True)
        if not access.has_subscription_history:
            return
        if access.subscription is None:
            self._raise_inactive_subscription(access.organization_id)
        limit = access.plan.max_sucursales
        if limit is None:
            return

        active_count = self.db.scalar(
            select(func.count(Sucursal.id_sucursal)).where(
                Sucursal.id_organizacion == access.organization_id,
                Sucursal.estado == "ACTIVA",
            )
        ) or 0
        if active_count >= limit:
            raise HTTPException(403, detail={
                "code": "PLAN_LIMIT_REACHED",
                "message": f"El plan {access.plan.nombre} permite hasta {limit} sucursales activas.",
                "resource": "sucursales_activas",
                "limit": limit,
                "current": active_count,
                "plan": access.plan.codigo,
            })

    def require_feature(self, feature_code: str, *, commit_expiration: bool = True) -> PlanAccess:
        access = self.resolve(commit_expiration=commit_expiration)
        if not access.has_subscription_history:
            return access
        if access.subscription is None:
            self._raise_inactive_subscription(access.organization_id)

        codes = ("reportes_ia", "reportes_gemini") if feature_code in {"reportes_ia", "reportes_gemini"} else (feature_code,)
        rows = self.db.scalars(select(PlanCaracteristica).where(
            PlanCaracteristica.plan_id == access.subscription.plan_id,
            PlanCaracteristica.codigo.in_(codes),
        )).all()
        by_code = {row.codigo: row for row in rows}
        # Prefer an explicitly configured canonical capability. Use the legacy
        # code only while a plan has not yet received its canonical row.
        feature = by_code.get("reportes_ia", by_code.get("reportes_gemini")) if len(codes) > 1 else by_code.get(feature_code)
        if feature is None or not feature.habilitada:
            raise HTTPException(403, detail={
                "code": "PLAN_FEATURE_NOT_INCLUDED",
                "message": f"La característica '{feature_code}' no está habilitada en el plan contratado.",
                "feature": feature_code,
                "plan": access.plan.codigo,
            })
        return access

    def _raise_inactive_subscription(self, organization_id: int) -> None:
        latest = self.db.scalar(
            select(Suscripcion)
            .where(Suscripcion.organizacion_id == organization_id)
            .order_by(Suscripcion.fecha_inicio.desc(), Suscripcion.id_suscripcion.desc())
            .limit(1)
        )
        expired = latest is not None and latest.estado == "VENCIDA"
        code = "SUBSCRIPTION_EXPIRED" if expired else "SUBSCRIPTION_REQUIRED"
        message = (
            "La suscripción de la organización venció. Renueve el plan para continuar."
            if expired
            else "La organización necesita una suscripción activa para usar esta capacidad."
        )
        raise HTTPException(403, detail={
            "code": code,
            "message": message,
            "organizacion_id": organization_id,
        })


def require_plan_feature(feature_code: str):
    """FastAPI dependency factory for premium endpoints when implemented."""

    def check_feature(
        db: Session = Depends(get_db),
        _: Usuario = Depends(get_current_user),
    ) -> PlanAccess:
        return PlanAccessService(db).require_feature(feature_code)

    return check_feature
