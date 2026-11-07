from datetime import timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_platform_admin, require_roles
from app.database.database import get_db
from app.models.usuario import Usuario
from app.schemas.subscription import (
    AvailablePlanResponse,
    SubscriptionAssignRequest,
    SubscriptionResponse,
)
from app.services.subscription_service import SubscriptionService


subscription_router = APIRouter(tags=["Suscripciones SaaS"])


def _plan_response(plan) -> dict:
    return {
        "id_plan": plan.id_plan,
        "codigo": plan.codigo,
        "nombre": plan.nombre,
        "descripcion": plan.descripcion,
        "max_sucursales": plan.max_sucursales,
        "caracteristicas": [
            {
                "id_plan_caracteristica": feature.id_plan_caracteristica,
                "codigo": feature.codigo,
                "nombre": feature.nombre,
                "descripcion": feature.descripcion,
                "habilitada": feature.habilitada,
                "limite": feature.limite,
                "configuracion": feature.configuracion,
            }
            for feature in plan.caracteristicas
        ],
    }


def _subscription_response(subscription) -> dict:
    if subscription is None:
        return None
    def utc(value):
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)

    return {
        "id_suscripcion": subscription.id_suscripcion,
        "organizacion_id": subscription.organizacion_id,
        "plan_id": subscription.plan_id,
        "plan_codigo": subscription.plan.codigo,
        "plan_nombre": subscription.plan.nombre,
        "estado": subscription.estado,
        "fecha_inicio": utc(subscription.fecha_inicio),
        "fecha_fin": utc(subscription.fecha_fin),
        "fecha_creacion": utc(subscription.fecha_creacion),
        "fecha_actualizacion": utc(subscription.fecha_actualizacion),
        "creado_por_id": subscription.creado_por_id,
    }


@subscription_router.get("/subscriptions/plans", response_model=list[AvailablePlanResponse])
def list_available_plans(
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_roles("ADMINISTRADOR", "ADMINISTRADOR_PLATAFORMA")),
):
    return [_plan_response(plan) for plan in SubscriptionService(db).list_available_plans()]


@subscription_router.get("/subscriptions/current", response_model=SubscriptionResponse | None)
def get_current_subscription(
    db: Session = Depends(get_db), current_user: Usuario = Depends(require_roles("ADMINISTRADOR"))
):
    return _subscription_response(SubscriptionService(db).current(current_user.id_organizacion))


@subscription_router.get("/subscriptions/history", response_model=list[SubscriptionResponse])
def get_subscription_history(
    db: Session = Depends(get_db), current_user: Usuario = Depends(require_roles("ADMINISTRADOR"))
):
    service = SubscriptionService(db)
    return [_subscription_response(row) for row in service.history(current_user.id_organizacion)]


@subscription_router.get(
    "/platform/organizations/{organization_id}/subscriptions/current",
    response_model=SubscriptionResponse | None,
)
def get_platform_current_subscription(
    organization_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_platform_admin),
):
    return _subscription_response(SubscriptionService(db).current(organization_id))


@subscription_router.get(
    "/platform/organizations/{organization_id}/subscriptions/history",
    response_model=list[SubscriptionResponse],
)
def get_platform_subscription_history(
    organization_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_platform_admin),
):
    service = SubscriptionService(db)
    return [_subscription_response(row) for row in service.history(organization_id)]


@subscription_router.post(
    "/platform/organizations/{organization_id}/subscriptions",
    response_model=SubscriptionResponse,
    status_code=201,
)
def assign_subscription(
    organization_id: int,
    request: SubscriptionAssignRequest,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(get_current_platform_admin),
):
    row = SubscriptionService(db).assign(organization_id, request.plan_id, actor.id_usuario, request.fecha_fin)
    return _subscription_response(row)


@subscription_router.put(
    "/platform/organizations/{organization_id}/subscriptions/current",
    response_model=SubscriptionResponse,
)
def change_subscription(
    organization_id: int,
    request: SubscriptionAssignRequest,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(get_current_platform_admin),
):
    row = SubscriptionService(db).change(organization_id, request.plan_id, actor.id_usuario, request.fecha_fin)
    return _subscription_response(row)


@subscription_router.post(
    "/platform/organizations/{organization_id}/subscriptions/current/cancel",
    response_model=SubscriptionResponse,
)
def cancel_subscription(
    organization_id: int,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(get_current_platform_admin),
):
    return _subscription_response(SubscriptionService(db).cancel(organization_id, actor.id_usuario))
