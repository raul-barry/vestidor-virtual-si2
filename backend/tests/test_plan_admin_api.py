from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select

from conftest import session_token
from app.main import app
from app.models.plan import Plan, PlanCaracteristica
from app.models.rol import Rol
from app.models.suscripcion import Suscripcion
from app.models.usuario import Usuario


def _headers(db, role_name: str, email: str):
    role = db.scalar(select(Rol).where(Rol.nombre == role_name))
    if role is None:
        role = Rol(nombre=role_name, estado="ACTIVO")
        db.add(role)
        db.flush()
    user = Usuario(id_organizacion=None if role_name == "ADMINISTRADOR_PLATAFORMA" else 1,
                   id_rol=role.id_rol, nombres="Test", apellidos="Admin",
                   correo=email, password_hash="not-used", estado="ACTIVO")
    db.add(user)
    db.commit()
    token = session_token(db, {"id_usuario": user.id_usuario, "rol": role_name})
    return {"Authorization": f"Bearer {token}"}


def _plan(db):
    plan = Plan(codigo="ESTILO", nombre="Plan Estilo", descripcion="Inicial", max_sucursales=2, activo=True)
    plan.caracteristicas = [
        PlanCaracteristica(codigo="catalogo", nombre="Catálogo", habilitada=True,
                           limite=None, configuracion={"offline": False}),
        PlanCaracteristica(codigo="reportes_gemini", nombre="Reportes Gemini", habilitada=False),
    ]
    db.add(plan)
    db.commit()
    return plan


def test_platform_admin_can_read_and_update_plan_and_features_are_reflected(db):
    db.info.pop("organization_id", None)
    plan = _plan(db)
    platform = _headers(db, "ADMINISTRADOR_PLATAFORMA", "plan-platform@example.test")
    client = TestClient(app)

    listed = client.get("/api/platform/plans", headers=platform)
    detail = client.get(f"/api/platform/plans/{plan.id_plan}", headers=platform)
    updated = client.put(f"/api/platform/plans/{plan.id_plan}", headers=platform,
                         json={"nombre": "Estilo Plus", "descripcion": "Ajustado", "max_sucursales": 3})
    features = client.put(f"/api/platform/plans/{plan.id_plan}/features", headers=platform, json={
        "caracteristicas": [
            {"codigo": "catalogo", "habilitada": False, "limite": 50,
             "configuracion": {"offline": True, "modo": "lectura"}},
            {"codigo": "reportes_ia", "habilitada": True},
        ]
    })
    public_plans = client.get("/api/subscriptions/plans", headers=platform)

    assert listed.status_code == 200 and len(listed.json()) == 1
    assert detail.json()["caracteristicas"][0]["codigo"] == "catalogo"
    assert updated.status_code == 200 and updated.json()["max_sucursales"] == 3
    assert features.status_code == 200
    by_code = {feature["codigo"]: feature for feature in features.json()["caracteristicas"]}
    assert by_code["catalogo"]["habilitada"] is False
    assert by_code["catalogo"]["limite"] == 50
    assert by_code["catalogo"]["configuracion"] == {"offline": True, "modo": "lectura"}
    assert by_code["reportes_ia"]["habilitada"] is True
    assert public_plans.json()[0]["nombre"] == "Estilo Plus"
    assert {feature["codigo"]: feature["habilitada"] for feature in public_plans.json()[0]["caracteristicas"]}["reportes_ia"] is True


def test_company_admin_cannot_access_or_modify_global_plans(db):
    db.info.pop("organization_id", None)
    plan = _plan(db)
    admin = _headers(db, "ADMINISTRADOR", "plan-company@example.test")
    employee = _headers(db, "ENCARGADO_SUCURSAL", "plan-employee@example.test")
    client = TestClient(app)
    for headers in (admin, employee):
        assert client.get("/api/platform/plans", headers=headers).status_code == 403
        assert client.get(f"/api/platform/plans/{plan.id_plan}", headers=headers).status_code == 403
        assert client.put(f"/api/platform/plans/{plan.id_plan}", headers=headers,
                          json={"nombre": "No autorizado"}).status_code == 403
        assert client.put(f"/api/platform/plans/{plan.id_plan}/features", headers=headers,
                          json={"caracteristicas": [{"codigo": "catalogo", "habilitada": False}]}).status_code == 403


def test_plan_with_active_subscription_cannot_be_deactivated(db):
    db.info.pop("organization_id", None)
    plan = _plan(db)
    db.add(Suscripcion(organizacion_id=1, plan_id=plan.id_plan, estado="ACTIVA",
                       fecha_inicio=datetime.now(timezone.utc)))
    db.commit()
    platform = _headers(db, "ADMINISTRADOR_PLATAFORMA", "plan-active-sub@example.test")
    client = TestClient(app)

    response = client.put(f"/api/platform/plans/{plan.id_plan}", headers=platform, json={"activo": False})

    assert response.status_code == 409
    db.refresh(plan)
    assert plan.activo is True


def test_plan_feature_update_rejects_unknown_or_duplicate_codes(db):
    db.info.pop("organization_id", None)
    plan = _plan(db)
    platform = _headers(db, "ADMINISTRADOR_PLATAFORMA", "plan-validation@example.test")
    client = TestClient(app)
    unknown = client.put(f"/api/platform/plans/{plan.id_plan}/features", headers=platform,
                         json={"caracteristicas": [{"codigo": "missing", "habilitada": True}]})
    duplicate = client.put(f"/api/platform/plans/{plan.id_plan}/features", headers=platform,
                           json={"caracteristicas": [{"codigo": "catalogo", "habilitada": True},
                                                       {"codigo": "catalogo", "habilitada": False}]})
    duplicate_alias = client.put(f"/api/platform/plans/{plan.id_plan}/features", headers=platform,
                                 json={"caracteristicas": [{"codigo": "reportes_ia", "habilitada": True},
                                                             {"codigo": "reportes_gemini", "habilitada": False}]})
    assert unknown.status_code == 404
    assert duplicate.status_code == 422
    assert duplicate_alias.status_code == 422
