from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select

from conftest import session_token
from app.core.exceptions import AppException
from app.main import app
from app.models.audit_log import AuditLog
from app.models.organizacion import Organizacion
from app.models.plan import Plan
from app.models.rol import Rol
from app.models.usuario import Usuario
from app.services.tenant_provisioning_service import TenantProvisioningService


def _platform_headers(db):
    # A SaaS platform administrator has no tenant scope; the fixture defaults
    # ordinary records to organization 1 unless that context is cleared.
    db.info.pop("organization_id", None)
    role = db.scalar(select(Rol).where(Rol.nombre == "ADMINISTRADOR_PLATAFORMA"))
    if role is None:
        role = Rol(nombre="ADMINISTRADOR_PLATAFORMA", estado="ACTIVO")
        db.add(role)
        db.flush()
    admin_role = db.scalar(select(Rol).where(Rol.nombre == "ADMINISTRADOR"))
    if admin_role is None:
        db.add(Rol(nombre="ADMINISTRADOR", estado="ACTIVO"))
    user = Usuario(id_organizacion=None, id_rol=role.id_rol, nombres="Platform", apellidos="Admin",
                   correo="provision-platform@example.test", password_hash="hash", estado="ACTIVO")
    db.add(user)
    db.commit()
    return {"Authorization": f"Bearer {session_token(db, {'id_usuario': user.id_usuario, 'rol': role.nombre})}"}


def _payload(end=None):
    return {
        "organization": {"nombre": "Nueva Empresa", "razon_social": "Nueva Empresa SRL", "nit": "987654321",
                         "correo_contacto": "contacto@nueva.example", "telefono_contacto": "+591 70000000",
                         "direccion": "Calle Uno", "slug": "nueva-empresa"},
        "administrator": {"nombres": "Ana", "apellidos": "Paz", "correo": "ana@nueva.example",
                           "telefono": "+591 71111111", "password": "una-clave-segura-123"},
        "subscription": {"plan_id": 1, **({"fecha_fin": end} if end is not None else {})},
    }


def test_provisioning_creates_tenant_admin_subscription_and_audit(db):
    headers = _platform_headers(db)
    db.add(Plan(id_plan=1, codigo="ESTILO", nombre="Plan Estilo", max_sucursales=2, activo=True))
    db.commit()
    response = TestClient(app).post("/api/platform/organizations/provision", headers=headers, json=_payload())
    assert response.status_code == 201, response.text
    body = response.json()
    organization_id = body["organization"]["id_organizacion"]
    assert body["administrator"]["rol"] == "ADMINISTRADOR"
    assert body["administrator"]["id_organizacion"] == organization_id
    assert body["subscription"]["plan_codigo"] == "ESTILO"
    assert "password" not in str(body).lower()
    db.info.pop("organization_id", None)
    events = db.scalars(select(AuditLog).where(AuditLog.organizacion_id == organization_id)).all()
    assert {event.accion for event in events} >= {"ORGANIZACION_CREADA", "USUARIO_CREADO", "SUSCRIPCION_ASIGNADA"}
    assert all(event.usuario_id is not None for event in events)


def test_provisioning_rejects_duplicate_company_and_admin_fields(db):
    headers = _platform_headers(db)
    db.add(Plan(id_plan=1, codigo="ESTILO", nombre="Plan Estilo", max_sucursales=2, activo=True))
    db.commit()
    db.info.pop("organization_id", None)
    client = TestClient(app)
    first = client.post("/api/platform/organizations/provision", headers=headers, json=_payload())
    assert first.status_code == 201
    duplicate_nit = _payload(); duplicate_nit["organization"]["slug"] = "otro-slug"
    assert client.post("/api/platform/organizations/provision", headers=headers, json=duplicate_nit).status_code == 409
    duplicate_slug = _payload(); duplicate_slug["organization"]["nit"] = "111222333"
    assert client.post("/api/platform/organizations/provision", headers=headers, json=duplicate_slug).status_code == 409
    duplicate_email = _payload(); duplicate_email["organization"]["nit"] = "111222333"; duplicate_email["organization"]["slug"] = "otro-slug"
    assert client.post("/api/platform/organizations/provision", headers=headers, json=duplicate_email).status_code == 409


def test_provisioning_rejects_unknown_inactive_plans_and_invalid_dates(db):
    headers = _platform_headers(db)
    db.add_all([Plan(id_plan=1, codigo="ESTILO", nombre="Plan Estilo", max_sucursales=2, activo=True),
                Plan(id_plan=2, codigo="PAUSADO", nombre="Pausado", max_sucursales=1, activo=False)])
    db.commit()
    client = TestClient(app)
    missing = _payload(); missing["subscription"]["plan_id"] = 99
    inactive = _payload(); inactive["subscription"]["plan_id"] = 2
    invalid_date = _payload((datetime.now(timezone.utc) - timedelta(days=1)).isoformat())
    assert client.post("/api/platform/organizations/provision", headers=headers, json=missing).status_code == 404
    assert client.post("/api/platform/organizations/provision", headers=headers, json=inactive).status_code == 404
    assert client.post("/api/platform/organizations/provision", headers=headers, json=invalid_date).status_code == 422
    assert db.scalar(select(Organizacion).where(Organizacion.slug == "nueva-empresa")) is None


def test_only_platform_admin_can_provision(db):
    headers = _platform_headers(db)
    company_role = db.scalar(select(Rol).where(Rol.nombre == "ADMINISTRADOR"))
    company_admin = Usuario(id_organizacion=1, id_rol=company_role.id_rol, nombres="Company", apellidos="Admin",
                            correo="company-admin-provision@example.test", password_hash="hash", estado="ACTIVO")
    db.add(company_admin)
    db.commit()
    company_headers = {"Authorization": f"Bearer {session_token(db, {'id_usuario': company_admin.id_usuario, 'rol': company_role.nombre})}"}
    response = TestClient(app).post("/api/platform/organizations/provision", headers=company_headers, json=_payload())
    assert response.status_code == 403


def test_provisioning_rolls_back_everything_if_subscription_creation_fails(db, monkeypatch):
    from app.services.subscription_service import SubscriptionService
    actor_role = db.scalar(select(Rol).where(Rol.nombre == "ADMINISTRADOR_PLATAFORMA"))
    if actor_role is None:
        actor_role = Rol(nombre="ADMINISTRADOR_PLATAFORMA", estado="ACTIVO")
        admin_role = Rol(nombre="ADMINISTRADOR", estado="ACTIVO")
        db.add_all([actor_role, admin_role])
        db.flush()
    actor = Usuario(id_organizacion=1, id_rol=actor_role.id_rol, nombres="P", apellidos="A",
                    correo="rollback-platform@example.test", password_hash="hash", estado="ACTIVO")
    db.add(actor)
    db.add(Plan(id_plan=1, codigo="ESTILO", nombre="Plan Estilo", max_sucursales=2, activo=True))
    db.commit()
    def fail(*args, **kwargs):
        raise AppException("fallo provocado", status_code=500)
    monkeypatch.setattr(SubscriptionService, "assign", fail)
    try:
        TenantProvisioningService(db).provision(
            __import__("app.schemas.organization_admin", fromlist=["TenantProvisionRequest"]).TenantProvisionRequest.model_validate(_payload()),
            actor,
        )
        assert False, "expected failure"
    except AppException:
        pass
    assert db.scalar(select(Organizacion).where(Organizacion.slug == "nueva-empresa")) is None
    assert db.scalar(select(Usuario.id_usuario).where(Usuario.correo == "ana@nueva.example")) is None
    assert db.scalar(select(AuditLog.id).where(AuditLog.accion == "ORGANIZACION_CREADA")) is None
