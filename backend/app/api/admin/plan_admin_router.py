from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_platform_admin
from app.database.database import get_db
from app.models.usuario import Usuario
from app.schemas.plan_admin import PlanAdminResponse, PlanAdminUpdate, PlanFeaturesAdminUpdate
from app.services.plan_admin_service import PlanAdminService

plan_admin_router = APIRouter(prefix="/platform/plans", tags=["Administración de planes"])


@plan_admin_router.get("", response_model=list[PlanAdminResponse])
def list_plans(db: Session = Depends(get_db), _: Usuario = Depends(get_current_platform_admin)):
    return PlanAdminService(db).list()


@plan_admin_router.get("/{plan_id}", response_model=PlanAdminResponse)
def get_plan(plan_id: int, db: Session = Depends(get_db), _: Usuario = Depends(get_current_platform_admin)):
    return PlanAdminService(db).get(plan_id)


@plan_admin_router.put("/{plan_id}", response_model=PlanAdminResponse)
def update_plan(plan_id: int, data: PlanAdminUpdate, db: Session = Depends(get_db), _: Usuario = Depends(get_current_platform_admin)):
    return PlanAdminService(db).update(plan_id, data)


@plan_admin_router.put("/{plan_id}/features", response_model=PlanAdminResponse)
def update_plan_features(plan_id: int, data: PlanFeaturesAdminUpdate, db: Session = Depends(get_db), _: Usuario = Depends(get_current_platform_admin)):
    return PlanAdminService(db).update_features(plan_id, data)
