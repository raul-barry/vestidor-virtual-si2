from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.exceptions import AppException
from app.models.audit_log import AuditLog
from app.models.organizacion import Organizacion
from app.models.plan import Plan
from app.models.suscripcion import Suscripcion
from app.services.audit_service import AuditService


class SubscriptionService:
    """Single place for subscription state transitions and their audit events."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_available_plans(self) -> list[Plan]:
        return self.db.scalars(
            select(Plan).where(Plan.activo.is_(True))
            .options(selectinload(Plan.caracteristicas)).order_by(Plan.id_plan)
        ).all()

    def current(self, organization_id: int, *, commit_expiration: bool = True) -> Suscripcion | None:
        self._ensure_organization(organization_id)
        self.expire_due(organization_id, commit=commit_expiration)
        return self.db.scalar(
            select(Suscripcion).options(joinedload(Suscripcion.plan))
            .where(Suscripcion.organizacion_id == organization_id, Suscripcion.estado == "ACTIVA")
            .order_by(Suscripcion.fecha_inicio.desc(), Suscripcion.id_suscripcion.desc())
        )

    def history(self, organization_id: int, *, commit_expiration: bool = True) -> list[Suscripcion]:
        self._ensure_organization(organization_id)
        self.expire_due(organization_id, commit=commit_expiration)
        return self.db.scalars(
            select(Suscripcion).options(joinedload(Suscripcion.plan))
            .where(Suscripcion.organizacion_id == organization_id)
            .order_by(Suscripcion.fecha_inicio.desc(), Suscripcion.id_suscripcion.desc())
        ).all()

    def assign(
        self, organization_id: int, plan_id: int, actor_id: int,
        fecha_fin: datetime | None = None, *, commit: bool = True,
    ) -> Suscripcion:
        self._lock_organization(organization_id)
        self.expire_due(organization_id, commit=False)
        if self.current(organization_id, commit_expiration=False) is not None:
            raise AppException("La organización ya tiene una suscripción activa; use el cambio de plan", status_code=409)
        plan = self._active_plan(plan_id)
        previous_exists = self.db.scalar(
            select(Suscripcion.id_suscripcion).where(Suscripcion.organizacion_id == organization_id).limit(1)
        ) is not None
        action = "SUSCRIPCION_RENOVADA" if previous_exists else "SUSCRIPCION_ASIGNADA"
        return self._create(organization_id, plan, actor_id, fecha_fin, action=action, commit=commit)

    def change(self, organization_id: int, plan_id: int, actor_id: int, fecha_fin: datetime | None = None) -> Suscripcion:
        self._lock_organization(organization_id)
        self.expire_due(organization_id, commit=False)
        current = self.current(organization_id, commit_expiration=False)
        if current is None:
            raise AppException("No existe una suscripción activa para cambiar", status_code=404)
        plan = self._active_plan(plan_id)
        if current.plan_id == plan.id_plan:
            raise AppException("La organización ya tiene asignado ese plan", status_code=409)

        now = datetime.now(timezone.utc)
        previous_plan_id = current.plan_id
        current.estado = "FINALIZADA"
        current.fecha_actualizacion = now
        replacement = Suscripcion(
            organizacion_id=organization_id, plan_id=plan.id_plan, estado="ACTIVA",
            fecha_inicio=now, fecha_fin=fecha_fin, creado_por_id=actor_id,
        )
        self.db.add(replacement)
        try:
            self.db.flush()
            self._audit(
                replacement, "SUSCRIPCION_CAMBIO_PLAN", actor_id=actor_id,
                details={"suscripcion_anterior_id": current.id_suscripcion,
                         "plan_anterior_id": previous_plan_id, "plan_nuevo_id": plan.id_plan},
            )
            return self._commit(replacement)
        except IntegrityError as exc:
            self.db.rollback()
            raise AppException("No se pudo guardar el cambio de plan", status_code=409) from exc

    def cancel(self, organization_id: int, actor_id: int | None = None) -> Suscripcion:
        self._lock_organization(organization_id)
        self.expire_due(organization_id, commit=False)
        current = self.current(organization_id, commit_expiration=False)
        if current is None:
            raise AppException("No existe una suscripción activa para cancelar", status_code=404)
        self._transition(current, "CANCELADA", "SUSCRIPCION_CANCELADA", actor_id=actor_id)
        return self._commit(current)

    def expire_due(
        self, organization_id: int | None = None, *, now: datetime | None = None, commit: bool = True,
    ) -> int:
        """Mark only active subscriptions whose end date has passed; preserve history."""
        instant = self._utc(now or datetime.now(timezone.utc))
        query = select(Suscripcion).where(
            Suscripcion.estado == "ACTIVA", Suscripcion.fecha_fin.is_not(None), Suscripcion.fecha_fin <= instant,
        ).order_by(Suscripcion.id_suscripcion).with_for_update()
        if organization_id is not None:
            query = query.where(Suscripcion.organizacion_id == organization_id)
        rows = self.db.scalars(query).all()
        for subscription in rows:
            if subscription.estado == "ACTIVA":
                self._transition(subscription, "VENCIDA", "SUSCRIPCION_VENCIDA")
        if rows and commit:
            self.db.commit()
        return len(rows)

    def process_lifecycle(self, *, expiring_within_days: int = 30, now: datetime | None = None) -> dict[str, int]:
        """Idempotent daily job: expire due rows and audit first entry into warning window."""
        if expiring_within_days < 1 or expiring_within_days > 365:
            raise ValueError("expiring_within_days debe estar entre 1 y 365")
        self.db.info.pop("organization_id", None)
        instant = self._utc(now or datetime.now(timezone.utc))
        expired_count = self.expire_due(now=instant, commit=False)
        cutoff = instant + timedelta(days=expiring_within_days)
        upcoming = self.db.scalars(
            select(Suscripcion).options(joinedload(Suscripcion.plan))
            .where(Suscripcion.estado == "ACTIVA", Suscripcion.fecha_fin.is_not(None),
                   Suscripcion.fecha_fin > instant, Suscripcion.fecha_fin <= cutoff)
            .order_by(Suscripcion.fecha_fin, Suscripcion.id_suscripcion)
            .with_for_update()
        ).all()
        new_warning_count = 0
        for subscription in upcoming:
            key = f"subscription-expiring:{subscription.id_suscripcion}"
            exists = self.db.scalar(select(AuditLog.id).where(AuditLog.dedupe_key == key)) is not None
            if not exists:
                remaining = self._utc(subscription.fecha_fin) - instant
                AuditService.record(
                    self.db, organization_id=subscription.organizacion_id,
                    actor_id=None, actor_role="SISTEMA", action="SUSCRIPCION_PROXIMA_VENCER",
                    entity="Suscripcion", entity_id=subscription.id_suscripcion,
                    details={"dias_restantes": max(0, remaining.days),
                             "fecha_fin": self._utc(subscription.fecha_fin).isoformat()},
                    dedupe_key=key,
                )
                new_warning_count += 1
        if expired_count or new_warning_count:
            self.db.commit()
        return {"vencidas": expired_count, "proximas_a_vencer": len(upcoming),
                "avisos_nuevos": new_warning_count}

    def _transition(
        self, subscription: Suscripcion, state: str, action: str, *, actor_id: int | None = None,
    ) -> None:
        if subscription.estado != "ACTIVA":
            raise AppException("Solo se puede cambiar una suscripción activa", status_code=409)
        previous = subscription.estado
        subscription.estado = state
        subscription.fecha_actualizacion = datetime.now(timezone.utc)
        key = f"subscription-transition:{subscription.id_suscripcion}:{state}"
        self._audit(subscription, action, actor_id=actor_id,
                    details={"estado_anterior": previous, "estado_nuevo": state}, dedupe_key=key)

    def _audit(
        self, subscription: Suscripcion, action: str, *, actor_id: int | None = None,
        details: dict | None = None, dedupe_key: str | None = None,
    ) -> None:
        self.db.flush()
        AuditService.record(
            self.db, organization_id=subscription.organizacion_id,
            actor_id=actor_id if actor_id is not None else self.db.info.get("audit_actor_id"),
            actor_role=self.db.info.get("audit_actor_role", "SISTEMA"),
            action=action, entity="Suscripcion", entity_id=subscription.id_suscripcion,
            details=details, dedupe_key=dedupe_key,
        )

    def _lock_organization(self, organization_id: int) -> Organizacion:
        organization = self.db.scalar(
            select(Organizacion).where(Organizacion.id_organizacion == organization_id).with_for_update()
        )
        if organization is None:
            raise AppException("Organización no encontrada", status_code=404)
        return organization

    def _ensure_organization(self, organization_id: int) -> None:
        if self.db.get(Organizacion, organization_id) is None:
            raise AppException("Organización no encontrada", status_code=404)

    def _active_plan(self, plan_id: int) -> Plan:
        plan = self.db.get(Plan, plan_id)
        if plan is None or not plan.activo:
            raise AppException("Plan no encontrado o inactivo", status_code=404)
        return plan

    def _create(
        self, organization_id: int, plan: Plan, actor_id: int, fecha_fin: datetime | None,
        *, action: str, commit: bool = True,
    ) -> Suscripcion:
        subscription = Suscripcion(
            organizacion_id=organization_id, plan_id=plan.id_plan, estado="ACTIVA",
            fecha_inicio=datetime.now(timezone.utc), fecha_fin=fecha_fin, creado_por_id=actor_id,
        )
        self.db.add(subscription)
        try:
            self.db.flush()
            self._audit(subscription, action, actor_id=actor_id,
                        details={"plan_id": plan.id_plan, "estado": "ACTIVA"})
            return self._commit(subscription, commit=commit)
        except IntegrityError as exc:
            self.db.rollback()
            raise AppException("No se pudo guardar la suscripción: existe una activa o las referencias no son válidas", status_code=409) from exc

    def _commit(self, subscription: Suscripcion, *, commit: bool = True) -> Suscripcion:
        try:
            if commit:
                self.db.commit()
            else:
                self.db.flush()
        except IntegrityError as exc:
            self.db.rollback()
            raise AppException("No se pudo guardar la suscripción", status_code=409) from exc
        if commit:
            self.db.refresh(subscription)
        return subscription

    @staticmethod
    def _utc(value: datetime) -> datetime:
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
