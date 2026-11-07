from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select

from conftest import session_token
from app.main import app
from app.core.tenancy import set_organization_context
from app.models.organizacion import Organizacion
from app.models.plan import Plan, PlanCaracteristica
from app.models.rol import Rol
from app.models.suscripcion import Suscripcion
from app.models.usuario import Usuario
from app.services.plan_access_service import PlanAccessService


def _role_admin(db, organization_id: int = 1):
    role = db.scalar(select(Rol).where(Rol.nombre == "ADMINISTRADOR"))
    if role is None:
        role = Rol(nombre="ADMINISTRADOR", estado="ACTIVO")
        db.add(role)
        db.flush()
    user = Usuario(
        id_organizacion=organization_id,
        id_rol=role.id_rol,
        nombres="Admin",
        apellidos="Plan Test",
        correo=f"plan-admin-{organization_id}@example.test",
        password_hash="not-used",
        estado="ACTIVO",
    )
    db.add(user)
    db.commit()
    return {"Authorization": f"Bearer {session_token(db, {'id_usuario': user.id_usuario, 'rol': role.nombre})}"}


def _add_plan(db, code: str, max_branches: int | None, features: tuple[str, ...] = ()) -> Plan:
    plan = Plan(codigo=code, nombre=f"Plan {code}", max_sucursales=max_branches, activo=True)
    db.add(plan)
    db.flush()
    for feature_code in features:
        db.add(PlanCaracteristica(
            plan_id=plan.id_plan,
            codigo=feature_code,
            nombre=feature_code,
            habilitada=True,
        ))
    return plan


def _subscribe(db, organization_id: int, plan: Plan, *, end: datetime | None = None, state="ACTIVA"):
    row = Suscripcion(
        organizacion_id=organization_id,
        plan_id=plan.id_plan,
        estado=state,
        fecha_inicio=datetime.now(timezone.utc) - timedelta(minutes=1),
        fecha_fin=end,
    )
    db.add(row)
    return row


def _create_branch(client, headers, name: str):
    return client.post("/api/admin/branches", headers=headers,
                       json={"nombre": name, "direccion": "Calle de prueba", "ciudad": "Santa Cruz"})


def test_estilo_allows_two_active_branches_and_blocks_the_third(db):
    db.info.pop("organization_id", None)
    plan = _add_plan(db, "ESTILO", 2)
    _subscribe(db, 1, plan)
    db.commit()
    headers = _role_admin(db)
    client = TestClient(app)

    assert _create_branch(client, headers, "Estilo 1").status_code == 201
    assert _create_branch(client, headers, "Estilo 2").status_code == 201
    blocked = _create_branch(client, headers, "Estilo 3")

    assert blocked.status_code == 403
    assert blocked.json()["detail"]["code"] == "PLAN_LIMIT_REACHED"
    assert blocked.json()["detail"]["limit"] == 2
    assert blocked.json()["detail"]["current"] == 2


def test_moda_limit_is_ten_and_glamour_is_unlimited(db):
    db.info.pop("organization_id", None)
    db.add(Organizacion(id_organizacion=2, nombre="UrbanVogue", slug="urban-vogue", estado="ACTIVA"))
    db.add(Organizacion(id_organizacion=3, nombre="Glamour Shop", slug="glamour-shop", estado="ACTIVA"))
    moda, glamour = _add_plan(db, "MODA", 10), _add_plan(db, "GLAMOUR", None)
    _subscribe(db, 1, moda)
    _subscribe(db, 2, glamour)
    db.commit()
    client = TestClient(app)
    moda_headers, glamour_headers = _role_admin(db, 1), _role_admin(db, 2)

    moda_results = [_create_branch(client, moda_headers, f"Moda {i}") for i in range(1, 12)]
    assert [response.status_code for response in moda_results[:10]] == [201] * 10
    assert moda_results[10].status_code == 403
    assert moda_results[10].json()["detail"]["code"] == "PLAN_LIMIT_REACHED"

    glamour_results = [_create_branch(client, glamour_headers, f"Glamour {i}") for i in range(1, 12)]
    assert [response.status_code for response in glamour_results] == [201] * 11


def test_deactivation_is_allowed_at_capacity_and_frees_a_slot(db):
    db.info.pop("organization_id", None)
    plan = _add_plan(db, "ESTILO", 2)
    _subscribe(db, 1, plan)
    db.commit()
    client = TestClient(app)
    headers = _role_admin(db)
    first = _create_branch(client, headers, "Branch one").json()
    assert _create_branch(client, headers, "Branch two").status_code == 201

    assert client.patch(f"/api/admin/branches/{first['id_sucursal']}/toggle-status", headers=headers).status_code == 200
    assert _create_branch(client, headers, "Branch replacement").status_code == 201
    assert client.patch(f"/api/admin/branches/{first['id_sucursal']}/toggle-status", headers=headers).status_code == 403


def test_feature_matrix_and_tenant_isolation(db):
    db.info.pop("organization_id", None)
    db.add(Organizacion(id_organizacion=2, nombre="UrbanVogue", slug="urban-vogue", estado="ACTIVA"))
    db.add(Organizacion(id_organizacion=3, nombre="Glamour Shop", slug="glamour-shop", estado="ACTIVA"))
    estilo = _add_plan(db, "ESTILO", 2)
    moda = _add_plan(db, "MODA", 10, ("reportes_gemini",))
    glamour = _add_plan(db, "GLAMOUR", None, ("reportes_gemini", "machine_learning"))
    _subscribe(db, 1, estilo)
    _subscribe(db, 2, moda)
    _subscribe(db, 3, glamour)
    db.commit()

    set_organization_context(db, 1)
    with pytest.raises(HTTPException) as missing:
        PlanAccessService(db).require_feature("reportes_gemini")
    assert missing.value.detail["code"] == "PLAN_FEATURE_NOT_INCLUDED"

    set_organization_context(db, 2)
    assert PlanAccessService(db).require_feature("reportes_gemini").plan.codigo == "MODA"
    with pytest.raises(HTTPException) as moda_ml:
        PlanAccessService(db).require_feature("machine_learning")
    assert moda_ml.value.detail["code"] == "PLAN_FEATURE_NOT_INCLUDED"

    set_organization_context(db, 3)
    assert PlanAccessService(db).require_feature("machine_learning").plan.codigo == "GLAMOUR"


def test_expired_and_legacy_tenants_follow_compatibility_policy(db):
    db.info.pop("organization_id", None)
    plan = _add_plan(db, "MODA", 10, ("reportes_gemini",))
    expired = _subscribe(db, 1, plan, end=datetime.now(timezone.utc) - timedelta(seconds=1))
    db.commit()
    set_organization_context(db, 1)

    with pytest.raises(HTTPException) as error:
        PlanAccessService(db).require_feature("reportes_gemini")
    assert error.value.detail["code"] == "SUBSCRIPTION_EXPIRED"
    db.refresh(expired)
    assert expired.estado == "VENCIDA"
    expired_headers = _role_admin(db)
    expired_branch = _create_branch(TestClient(app), expired_headers, "Expired subscription branch")
    assert expired_branch.status_code == 403
    assert expired_branch.json()["detail"]["code"] == "SUBSCRIPTION_EXPIRED"
    db.refresh(expired)
    assert expired.estado == "VENCIDA"

    db.info.pop("organization_id", None)
    db.add(Organizacion(id_organizacion=2, nombre="Legacy Shop", slug="legacy-shop", estado="ACTIVA"))
    db.commit()
    set_organization_context(db, 2)
    access = PlanAccessService(db).require_feature("reportes_gemini")
    assert access.has_subscription_history is False
    legacy_headers = _role_admin(db, organization_id=2)
    legacy_branch = _create_branch(TestClient(app), legacy_headers, "Legacy tenant branch")
    assert legacy_branch.status_code == 201


def test_cancelled_tenant_requires_subscription(db):
    db.info.pop("organization_id", None)
    plan = _add_plan(db, "ESTILO", 2, ("reportes_gemini",))
    _subscribe(db, 1, plan, state="CANCELADA")
    db.commit()
    set_organization_context(db, 1)

    with pytest.raises(HTTPException) as error:
        PlanAccessService(db).require_feature("reportes_gemini")
    assert error.value.detail["code"] == "SUBSCRIPTION_REQUIRED"

    headers = _role_admin(db)
    blocked = _create_branch(TestClient(app), headers, "Canceled company new branch")
    assert blocked.status_code == 403
    assert blocked.json()["detail"]["code"] == "SUBSCRIPTION_REQUIRED"
