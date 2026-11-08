from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_platform_admin
from app.database.database import get_db
from app.models.usuario import Usuario
from app.schemas.plan_admin import PlanAdminResponse, PlanAdminUpdate, PlanFeaturesAdminUpdate
from app.services.plan_admin_service import PlanAdminService


def _plan_response(plan):
    canonical_exists = any(item.codigo == "reportes_ia" for item in plan.caracteristicas)
    features = []
    for item in plan.caracteristicas:
        if item.codigo == "reportes_gemini":
            if canonical_exists:
                continue
            code, name, description = "reportes_ia", "Reportes con IA", "Reportes empresariales asistidos por inteligencia artificial."
        else:
            code, name, description = item.codigo, item.nombre, item.descripcion
        features.append({"id_plan_caracteristica": item.id_plan_caracteristica,
                         "codigo": code, "nombre": name, "descripcion": description,
                         "habilitada": item.habilitada, "limite": item.limite,
                         "configuracion": item.configuracion})
    return {"id_plan": plan.id_plan, "codigo": plan.codigo, "nombre": plan.nombre,
            "descripcion": plan.descripcion, "max_sucursales": plan.max_sucursales,
            "activo": plan.activo, "caracteristicas": features}

plan_admin_router = APIRouter(prefix="/platform/plans", tags=["Administración de planes"])


@plan_admin_router.get("", response_model=list[PlanAdminResponse])
def list_plans(db: Session = Depends(get_db), _: Usuario = Depends(get_current_platform_admin)):
    return [_plan_response(plan) for plan in PlanAdminService(db).list()]


@plan_admin_router.get("/{plan_id}", response_model=PlanAdminResponse)
def get_plan(plan_id: int, db: Session = Depends(get_db), _: Usuario = Depends(get_current_platform_admin)):
    return _plan_response(PlanAdminService(db).get(plan_id))


@plan_admin_router.put("/{plan_id}", response_model=PlanAdminResponse)
def update_plan(plan_id: int, data: PlanAdminUpdate, db: Session = Depends(get_db), _: Usuario = Depends(get_current_platform_admin)):
    return _plan_response(PlanAdminService(db).update(plan_id, data))


@plan_admin_router.put("/{plan_id}/features", response_model=PlanAdminResponse)
def update_plan_features(plan_id: int, data: PlanFeaturesAdminUpdate, db: Session = Depends(get_db), _: Usuario = Depends(get_current_platform_admin)):
    return _plan_response(PlanAdminService(db).update_features(plan_id, data))
