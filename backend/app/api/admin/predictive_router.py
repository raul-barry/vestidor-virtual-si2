from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_current_admin
from app.database.database import get_db
from app.models.plan import PlanCaracteristica
from app.models.usuario import Usuario
from app.services.plan_access_service import PlanAccessService
from app.services.predictive_analytics_service import PredictiveAnalyticsService

predictive_router = APIRouter(
    prefix="/admin/reports/predictive", tags=["Machine Learning y dashboard predictivo"]
)

FEATURE_CODES = (
    "machine_learning",
    "prediccion_demanda",
    "segmentacion_kmeans",
    "dashboard_predictivo",
)


def _require_features(db: Session, *features: str) -> None:
    access_service = PlanAccessService(db)
    for feature in features:
        access_service.require_feature(feature)


@predictive_router.get("/features")
def predictive_features(
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_admin),
) -> dict[str, bool]:
    access = PlanAccessService(db).resolve()
    if not access.has_subscription_history:
        return {feature: True for feature in FEATURE_CODES}
    if access.subscription is None:
        return {feature: False for feature in FEATURE_CODES}
    enabled = set(db.scalars(select(PlanCaracteristica.codigo).where(
        PlanCaracteristica.plan_id == access.subscription.plan_id,
        PlanCaracteristica.habilitada.is_(True),
        PlanCaracteristica.codigo.in_(FEATURE_CODES),
    )).all())
    return {feature: feature in enabled for feature in FEATURE_CODES}


@predictive_router.get("/dashboard")
def predictive_dashboard(
    fecha_inicio: date | None = Query(default=None),
    fecha_fin: date | None = Query(default=None),
    id_sucursal: int | None = Query(default=None, gt=0),
    id_producto: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_admin),
) -> dict:
    _require_features(db, "machine_learning", "prediccion_demanda", "dashboard_predictivo")
    return PredictiveAnalyticsService(db).dashboard(
        fecha_inicio, fecha_fin, id_sucursal, id_producto
    )


@predictive_router.get("/segments")
def customer_segments(
    fecha_corte: date | None = Query(default=None),
    id_sucursal: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_admin),
) -> dict:
    _require_features(db, "machine_learning", "segmentacion_kmeans")
    return PredictiveAnalyticsService(db).segments(fecha_corte, id_sucursal)


@predictive_router.get("/history")
def predictive_history(
    fecha_inicio: date = Query(),
    fecha_fin: date = Query(),
    id_sucursal: int | None = Query(default=None, gt=0),
    id_producto: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_admin),
) -> dict:
    _require_features(db, "machine_learning", "prediccion_demanda", "dashboard_predictivo")
    return PredictiveAnalyticsService(db).history(
        fecha_inicio, fecha_fin, id_sucursal, id_producto
    )
