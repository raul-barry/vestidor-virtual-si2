from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.models.audit_log import AuditLog
from app.models.organizacion import Organizacion
from app.models.plan import Plan
from app.models.suscripcion import Suscripcion
from app.services.subscription_service import SubscriptionService


def test_lifecycle_job_expires_and_warns_once_without_suspending_tenants(db):
    db.info.pop("organization_id", None)
    db.add_all([
        Organizacion(id_organizacion=2, nombre="Urban Vogue", slug="urban-vogue", estado="ACTIVA"),
        Organizacion(id_organizacion=3, nombre="Elegance", slug="elegance", estado="INACTIVA"),
    ])
    plan = Plan(codigo="ESTILO", nombre="Plan Estilo", activo=True, max_sucursales=2)
    db.add(plan)
    db.flush()
    now = datetime(2035, 1, 10, 12, 0, tzinfo=timezone.utc)
    due = Suscripcion(organizacion_id=1, plan=plan, estado="ACTIVA", fecha_inicio=now - timedelta(days=40), fecha_fin=now - timedelta(seconds=1))
    upcoming = Suscripcion(organizacion_id=2, plan=plan, estado="ACTIVA", fecha_inicio=now - timedelta(days=10), fecha_fin=now + timedelta(days=9))
    historical = Suscripcion(organizacion_id=3, plan=plan, estado="CANCELADA", fecha_inicio=now - timedelta(days=60), fecha_fin=now - timedelta(days=30))
    db.add_all([due, upcoming, historical])
    db.commit()

    service = SubscriptionService(db)
    first = service.process_lifecycle(expiring_within_days=30, now=now)
    db.expire_all()
    assert first == {"vencidas": 1, "proximas_a_vencer": 1, "avisos_nuevos": 1}
    assert db.get(Organizacion, 1).estado == "ACTIVA"
    assert db.get(Organizacion, 3).estado == "INACTIVA"
    assert db.get(Suscripcion, due.id_suscripcion).estado == "VENCIDA"
    assert db.get(Suscripcion, upcoming.id_suscripcion).estado == "ACTIVA"
    assert db.get(Suscripcion, historical.id_suscripcion).estado == "CANCELADA"
    assert db.scalar(select(func.count(AuditLog.id)).where(AuditLog.accion == "SUSCRIPCION_VENCIDA")) == 1
    assert db.scalar(select(func.count(AuditLog.id)).where(AuditLog.accion == "SUSCRIPCION_PROXIMA_VENCER")) == 1

    second = service.process_lifecycle(expiring_within_days=30, now=now)
    assert second == {"vencidas": 0, "proximas_a_vencer": 1, "avisos_nuevos": 0}
    assert db.scalar(select(func.count(AuditLog.id)).where(AuditLog.accion == "SUSCRIPCION_VENCIDA")) == 1
    assert db.scalar(select(func.count(AuditLog.id)).where(AuditLog.accion == "SUSCRIPCION_PROXIMA_VENCER")) == 1


def test_assignment_after_expiry_is_audited_as_renewal(db):
    db.info.pop("organization_id", None)
    plan = Plan(codigo="MODA", nombre="Plan Moda", activo=True, max_sucursales=10)
    db.add(plan)
    old = Suscripcion(organizacion_id=1, plan=plan, estado="VENCIDA",
                      fecha_inicio=datetime.now(timezone.utc) - timedelta(days=40),
                      fecha_fin=datetime.now(timezone.utc) - timedelta(days=1))
    db.add(old)
    db.commit()
    service = SubscriptionService(db)
    replacement = service.assign(1, plan.id_plan, actor_id=None)
    assert replacement.estado == "ACTIVA"
    assert db.get(Suscripcion, old.id_suscripcion).estado == "VENCIDA"
    assert db.scalar(select(func.count(AuditLog.id)).where(AuditLog.accion == "SUSCRIPCION_RENOVADA")) == 1


def test_plan_change_and_cancel_have_semantic_audit_events(db):
    db.info.pop("organization_id", None)
    first = Plan(codigo="ESTILO", nombre="Plan Estilo", activo=True, max_sucursales=2)
    second = Plan(codigo="MODA", nombre="Plan Moda", activo=True, max_sucursales=10)
    db.add_all([first, second])
    db.commit()
    service = SubscriptionService(db)
    initial = service.assign(1, first.id_plan, actor_id=None)
    replacement = service.change(1, second.id_plan, actor_id=None)
    cancelled = service.cancel(1)
    assert initial.estado == "FINALIZADA"
    assert replacement.estado == cancelled.estado == "CANCELADA"
    assert db.scalar(select(func.count(AuditLog.id)).where(AuditLog.accion == "SUSCRIPCION_ASIGNADA")) == 1
    assert db.scalar(select(func.count(AuditLog.id)).where(AuditLog.accion == "SUSCRIPCION_CAMBIO_PLAN")) == 1
    assert db.scalar(select(func.count(AuditLog.id)).where(AuditLog.accion == "SUSCRIPCION_CANCELADA")) == 1
