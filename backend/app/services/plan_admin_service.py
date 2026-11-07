from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import AppException
from app.models.plan import Plan, PlanCaracteristica
from app.models.suscripcion import Suscripcion


class PlanAdminService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self) -> list[Plan]:
        return self.db.scalars(select(Plan).options(selectinload(Plan.caracteristicas)).order_by(Plan.id_plan)).all()

    def get(self, plan_id: int) -> Plan:
        plan = self.db.scalar(select(Plan).options(selectinload(Plan.caracteristicas)).where(Plan.id_plan == plan_id))
        if plan is None:
            raise AppException("Plan no encontrado", status_code=404)
        return plan

    def update(self, plan_id: int, data) -> Plan:
        plan = self.db.scalar(select(Plan).where(Plan.id_plan == plan_id).with_for_update())
        if plan is None:
            raise AppException("Plan no encontrado", status_code=404)
        values = data.model_dump(exclude_unset=True)
        if values.get("activo") is False and plan.activo:
            now = datetime.now(timezone.utc)
            active_subscription = self.db.scalar(select(Suscripcion.id_suscripcion).where(
                Suscripcion.plan_id == plan_id, Suscripcion.estado == "ACTIVA",
                (Suscripcion.fecha_fin.is_(None)) | (Suscripcion.fecha_fin > now),
            ).limit(1))
            if active_subscription is not None:
                raise AppException("No se puede desactivar el plan mientras tenga suscripciones activas", status_code=409)
        for field, value in values.items():
            setattr(plan, field, value)
        plan.fecha_actualizacion = datetime.now(timezone.utc)
        self.db.commit()
        return self.get(plan_id)

    def update_features(self, plan_id: int, data) -> Plan:
        plan = self.db.scalar(select(Plan).where(Plan.id_plan == plan_id).with_for_update())
        if plan is None:
            raise AppException("Plan no encontrado", status_code=404)
        features = {feature.codigo: feature for feature in self.db.scalars(
            select(PlanCaracteristica).where(PlanCaracteristica.plan_id == plan_id).with_for_update()
        ).all()}
        requested = data.caracteristicas
        missing = [item.codigo for item in requested if item.codigo not in features]
        if missing:
            raise AppException(f"Características no encontradas en este plan: {', '.join(missing)}", status_code=404)
        for item in requested:
            feature = features[item.codigo]
            for field, value in item.model_dump(exclude_unset=True, exclude={"codigo"}).items():
                setattr(feature, field, value)
        plan.fecha_actualizacion = datetime.now(timezone.utc)
        self.db.commit()
        return self.get(plan_id)
