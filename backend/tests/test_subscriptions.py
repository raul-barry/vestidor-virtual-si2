from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from conftest import session_token
from app.main import app
from app.models.organizacion import Organizacion
from app.models.plan import Plan
from app.models.rol import Rol
from app.models.suscripcion import Suscripcion
from app.models.usuario import Usuario


def _plan(db, code: str, *, active: bool = True) -> Plan:
    row = Plan(codigo=code, nombre=f"Plan {code}", activo=active, max_sucursales=3)
    db.add(row)
    db.flush()
    return row


def _headers(db, role_name: str, email: str, organization_id: int | None = 1) -> dict[str, str]:
    role = db.scalar(select(Rol).where(Rol.nombre == role_name))
    if role is None:
        role = Rol(nombre=role_name, estado="ACTIVO")
        db.add(role)
        db.flush()
    user = Usuario(
        id_organizacion=None if role_name == "ADMINISTRADOR_PLATAFORMA" else organization_id,
        id_rol=role.id_rol,
        nombres="Test",
        apellidos=role_name,
        correo=email,
        password_hash="not-used-in-this-test",
        estado="ACTIVO",
    )
    db.add(user)
    db.commit()
    token = session_token(db, {"id_usuario": user.id_usuario, "rol": role_name})
    return {"Authorization": f"Bearer {token}"}


def _platform_headers(db):
    return _headers(db, "ADMINISTRADOR_PLATAFORMA", "platform-subscriptions@example.test")


def test_assign_and_query_current_subscription_and_available_plans(db):
    db.info.pop("organization_id", None)
    plan = _plan(db, "ESTILO")
    db.commit()
    platform = _platform_headers(db)
    admin = _headers(db, "ADMINISTRADOR", "admin-subscriptions@example.test")
    client = TestClient(app)
    end = (datetime.now(timezone.utc) + timedelta(days=30)).astimezone(timezone(timedelta(hours=-4)))

    plans = client.get("/api/subscriptions/plans", headers=admin)
    naive_end = client.post(
        "/api/platform/organizations/1/subscriptions",
        headers=platform,
        json={"plan_id": plan.id_plan, "fecha_fin": "2035-01-01T12:00:00"},
    )
    created = client.post(
        "/api/platform/organizations/1/subscriptions",
        headers=platform,
        json={"plan_id": plan.id_plan, "fecha_fin": end.isoformat()},
    )
    current = client.get("/api/subscriptions/current", headers=admin)

    assert plans.status_code == 200
    assert [row["codigo"] for row in plans.json()] == ["ESTILO"]
    assert naive_end.status_code == 422
    assert created.status_code == 201, created.text
    assert created.json()["estado"] == "ACTIVA"
    assert created.json()["creado_por_id"] is not None
    returned_end = datetime.fromisoformat(created.json()["fecha_fin"].replace("Z", "+00:00"))
    assert returned_end.utcoffset() == timedelta(0)
    assert current.status_code == 200
    assert current.json()["id_suscripcion"] == created.json()["id_suscripcion"]


def test_change_plan_finalizes_previous_and_keeps_history(db):
    db.info.pop("organization_id", None)
    first, second, third = _plan(db, "ESTILO"), _plan(db, "MODA"), _plan(db, "GLAMOUR")
    db.commit()
    platform = _platform_headers(db)
    client = TestClient(app)
    initial = client.post("/api/platform/organizations/1/subscriptions", headers=platform,
                          json={"plan_id": first.id_plan})
    changed = client.put("/api/platform/organizations/1/subscriptions/current", headers=platform,
                         json={"plan_id": second.id_plan})
    history = client.get("/api/platform/organizations/1/subscriptions/history", headers=platform)
    current_after_reload = client.get("/api/platform/organizations/1/subscriptions/current", headers=platform)

    assert initial.status_code == 201, initial.text
    assert changed.status_code == 200, changed.text
    assert changed.json()["plan_codigo"] == "MODA"
    assert current_after_reload.status_code == 200
    assert current_after_reload.json()["id_suscripcion"] == changed.json()["id_suscripcion"]
    assert current_after_reload.json()["plan_codigo"] == "MODA"
    assert [row["estado"] for row in history.json()] == ["ACTIVA", "FINALIZADA"]
    assert {row["plan_codigo"] for row in history.json()} == {"ESTILO", "MODA"}

    changed_again = client.put("/api/platform/organizations/1/subscriptions/current", headers=platform,
                               json={"plan_id": third.id_plan})
    history_after_second_change = client.get(
        "/api/platform/organizations/1/subscriptions/history", headers=platform
    )
    assert changed_again.status_code == 200, changed_again.text
    assert changed_again.json()["plan_codigo"] == "GLAMOUR"
    assert [row["plan_codigo"] for row in history_after_second_change.json()] == ["GLAMOUR", "MODA", "ESTILO"]
    assert [row["estado"] for row in history_after_second_change.json()] == [
        "ACTIVA", "FINALIZADA", "FINALIZADA"
    ]


def test_change_rejects_missing_or_inactive_plan_without_changing_current(db):
    db.info.pop("organization_id", None)
    active, inactive = _plan(db, "ESTILO"), _plan(db, "INACTIVO", active=False)
    db.commit()
    platform = _platform_headers(db)
    client = TestClient(app)
    assigned = client.post("/api/platform/organizations/1/subscriptions", headers=platform,
                           json={"plan_id": active.id_plan})

    missing = client.put("/api/platform/organizations/1/subscriptions/current", headers=platform,
                         json={"plan_id": 999999})
    disabled = client.put("/api/platform/organizations/1/subscriptions/current", headers=platform,
                          json={"plan_id": inactive.id_plan})
    malformed = client.put("/api/platform/organizations/1/subscriptions/current", headers=platform,
                           json={"plan_id": 0})
    current = client.get("/api/platform/organizations/1/subscriptions/current", headers=platform)
    history = client.get("/api/platform/organizations/1/subscriptions/history", headers=platform)

    assert assigned.status_code == 201
    assert missing.status_code == 404
    assert disabled.status_code == 404
    assert malformed.status_code == 422
    assert current.json()["plan_codigo"] == "ESTILO"
    assert len(history.json()) == 1


def test_only_one_active_subscription_and_inactive_plans_cannot_be_assigned(db):
    db.info.pop("organization_id", None)
    plan, disabled = _plan(db, "ESTILO"), _plan(db, "INACTIVO", active=False)
    db.commit()
    platform = _platform_headers(db)
    client = TestClient(app)
    unavailable = client.post("/api/platform/organizations/1/subscriptions", headers=platform,
                              json={"plan_id": disabled.id_plan})
    first = client.post("/api/platform/organizations/1/subscriptions", headers=platform,
                        json={"plan_id": plan.id_plan})
    duplicate = client.post("/api/platform/organizations/1/subscriptions", headers=platform,
                            json={"plan_id": plan.id_plan})

    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert unavailable.status_code == 404
    assert db.scalar(select(Suscripcion.id_suscripcion).where(Suscripcion.estado == "ACTIVA")) is not None

    db.add(Suscripcion(organizacion_id=1, plan_id=plan.id_plan, estado="ACTIVA",
                       fecha_inicio=datetime.now(timezone.utc)))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_cancel_subscription_preserves_history(db):
    db.info.pop("organization_id", None)
    plan = _plan(db, "ESTILO")
    db.commit()
    platform = _platform_headers(db)
    client = TestClient(app)
    assigned = client.post("/api/platform/organizations/1/subscriptions", headers=platform,
                           json={"plan_id": plan.id_plan})
    cancelled = client.post("/api/platform/organizations/1/subscriptions/current/cancel", headers=platform)
    current = client.get("/api/platform/organizations/1/subscriptions/current", headers=platform)
    history = client.get("/api/platform/organizations/1/subscriptions/history", headers=platform)

    assert assigned.status_code == 201
    assert cancelled.status_code == 200
    assert cancelled.json()["estado"] == "CANCELADA"
    assert current.json() is None
    assert len(history.json()) == 1
    assert history.json()[0]["estado"] == "CANCELADA"


def test_expired_subscription_is_marked_when_subscription_is_read(db):
    db.info.pop("organization_id", None)
    plan = _plan(db, "ESTILO")
    db.add(Suscripcion(
        organizacion_id=1,
        plan=plan,
        estado="ACTIVA",
        fecha_inicio=datetime.now(timezone.utc) - timedelta(days=3),
        fecha_fin=datetime.now(timezone.utc) - timedelta(seconds=1),
    ))
    db.commit()
    admin = _headers(db, "ADMINISTRADOR", "expiry-admin@example.test")

    response = TestClient(app).get("/api/subscriptions/current", headers=admin)

    assert response.status_code == 200
    assert response.json() is None
    db.refresh(db.scalar(select(Suscripcion)))
    assert db.scalar(select(Suscripcion.estado)) == "VENCIDA"


def test_subscription_queries_are_tenant_scoped_and_mutations_require_platform_admin(db):
    db.info.pop("organization_id", None)
    db.add(Organizacion(id_organizacion=2, nombre="UrbanVogue", slug="urban-vogue", estado="ACTIVA"))
    plan = _plan(db, "ESTILO")
    db.add(Suscripcion(
        organizacion_id=2, plan=plan, estado="ACTIVA", fecha_inicio=datetime.now(timezone.utc)
    ))
    db.commit()
    company_admin = _headers(db, "ADMINISTRADOR", "tenant-one@example.test", organization_id=1)
    company_two_admin = _headers(db, "ADMINISTRADOR", "tenant-two@example.test", organization_id=2)
    employee = _headers(db, "ENCARGADO_SUCURSAL", "tenant-employee@example.test", organization_id=1)
    customer = _headers(db, "CLIENTE", "tenant-client@example.test", organization_id=1)
    client = TestClient(app)

    current = client.get("/api/subscriptions/current", headers=company_admin)
    history = client.get("/api/subscriptions/history", headers=company_admin)
    assert current.json() is None
    assert history.json() == []
    own_current = client.get("/api/subscriptions/current", headers=company_two_admin)
    assert own_current.status_code == 200
    assert own_current.json()["organizacion_id"] == 2
    assert client.get("/api/platform/organizations/2/subscriptions/history", headers=company_admin).status_code == 403
    assert client.post("/api/platform/organizations/1/subscriptions", headers=company_admin,
                       json={"plan_id": plan.id_plan}).status_code == 403
    assert client.put("/api/platform/organizations/2/subscriptions/current", headers=company_admin,
                      json={"plan_id": plan.id_plan}).status_code == 403
    for headers in (employee, customer):
        assert client.get("/api/subscriptions/current", headers=headers).status_code == 403
        assert client.get("/api/subscriptions/plans", headers=headers).status_code == 403
        assert client.post("/api/platform/organizations/1/subscriptions", headers=headers,
                           json={"plan_id": plan.id_plan}).status_code == 403
        assert client.put("/api/platform/organizations/1/subscriptions/current", headers=headers,
                          json={"plan_id": plan.id_plan}).status_code == 403
        assert client.post("/api/platform/organizations/1/subscriptions/current/cancel",
                           headers=headers).status_code == 403
