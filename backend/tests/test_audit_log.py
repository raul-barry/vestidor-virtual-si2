import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from conftest import session_token
from app.main import app
from app.models.audit_log import AuditLog
from app.models.rol import Rol
from app.models.sucursal import Sucursal
from app.models.usuario import Usuario


def _auth(db, role, email, organization=1):
    row = db.scalar(select(Rol).where(Rol.nombre == role))
    if row is None:
        row = Rol(nombre=role, estado="ACTIVO")
        db.add(row)
        db.flush()
    user = Usuario(id_organizacion=None if role == "ADMINISTRADOR_PLATAFORMA" else organization, id_rol=row.id_rol,
                   nombres="Test", apellidos="Audit", correo=email,
                   password_hash="secret-hash", estado="ACTIVO")
    db.add(user)
    db.commit()
    return {"Authorization": f"Bearer {session_token(db, {'id_usuario': user.id_usuario, 'rol': role})}"}


def test_branch_mutation_is_audited_and_sensitive_fields_are_not_exposed(db):
    headers = _auth(db, "ADMINISTRADOR", "audit-admin@example.test")
    client = TestClient(app)
    response = client.post("/api/admin/branches", headers=headers,
                           json={"nombre": "Auditoría Central", "direccion": "Calle 1", "ciudad": "La Paz"})
    assert response.status_code == 201
    row = db.scalar(select(AuditLog).where(AuditLog.organizacion_id == 1, AuditLog.entidad == "Sucursal").order_by(AuditLog.id.desc()))
    assert row is not None and row.usuario_id is not None and row.rol == "ADMINISTRADOR"
    assert row.entidad_id == str(response.json()["id_sucursal"])
    assert "password_hash" not in str(row.detalles)


def test_activity_routes_are_role_scoped_and_tenant_isolated(db):
    db.info.pop("organization_id", None)
    from app.models.organizacion import Organizacion
    db.add(Organizacion(id_organizacion=2, nombre="Otra", slug="otra", estado="ACTIVA"))
    db.commit()
    admin_one = _auth(db, "ADMINISTRADOR", "audit-one@example.test", 1)
    admin_two = _auth(db, "ADMINISTRADOR", "audit-two@example.test", 2)
    employee = _auth(db, "ENCARGADO_SUCURSAL", "audit-employee@example.test", 1)
    platform = _auth(db, "ADMINISTRADOR_PLATAFORMA", "audit-platform@example.test", 1)
    db.info.pop("organization_id", None)
    db.add(Sucursal(id_organizacion=1, nombre="A", direccion="A", ciudad="A", estado="ACTIVA"))
    db.add(Sucursal(id_organizacion=2, nombre="B", direccion="B", ciudad="B", estado="ACTIVA"))
    db.commit()
    client = TestClient(app)
    own = client.get("/api/organizations/me/activity?limit=1", headers=admin_one)
    assert own.status_code == 200 and own.json()["total"] >= 1 and len(own.json()["items"]) == 1
    assert all(item["organizacion_id"] == 1 for item in own.json()["items"])
    assert client.get("/api/platform/organizations/2/activity", headers=admin_two).status_code == 403
    assert client.get("/api/organizations/me/activity", headers=employee).status_code == 403
    assert client.get("/api/platform/organizations/1/activity", headers=employee).status_code == 403
    assert client.get("/api/platform/organizations/1/activity", headers=platform).status_code == 200


def test_audit_rows_are_immutable(db):
    row = AuditLog(organizacion_id=1, rol="SYSTEM", accion="TEST", entidad="Test", resultado="EXITOSO", detalles={})
    db.add(row)
    db.commit()
    row.accion = "EDITED"
    with pytest.raises(ValueError, match="inmutables"):
        db.commit()
    db.rollback()
    db.delete(row)
    with pytest.raises(ValueError, match="inmutables"):
        db.commit()


def test_activity_filters_and_pagination_are_scoped(db):
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select
    from app.models.organizacion import Organizacion
    db.info.pop("organization_id", None)
    db.add(Organizacion(id_organizacion=2, nombre="Otra", slug="otra", estado="ACTIVA"))
    db.commit()
    now = datetime.now(timezone.utc)
    _auth(db, "ADMINISTRADOR", "audit-filter-one@example.test", 1)
    _auth(db, "ADMINISTRADOR", "audit-filter-two@example.test", 1)
    _auth(db, "ADMINISTRADOR", "audit-filter-other@example.test", 2)
    users = db.scalars(
        select(Usuario).where(Usuario.correo.in_([
            "audit-filter-one@example.test",
            "audit-filter-two@example.test",
            "audit-filter-other@example.test",
        ]))
    ).all()
    users_by_email = {user.correo: user for user in users}
    user_one = users_by_email["audit-filter-one@example.test"]
    user_two = users_by_email["audit-filter-two@example.test"]
    user_other = users_by_email["audit-filter-other@example.test"]
    db.add_all([
        AuditLog(organizacion_id=1, usuario_id=user_one.id_usuario, rol="ADMINISTRADOR", accion="PEDIDO_CREADO", entidad="Pedido", fecha_hora=now, resultado="EXITOSO", detalles={}),
        AuditLog(organizacion_id=1, usuario_id=user_two.id_usuario, rol="ADMINISTRADOR", accion="PAGO_MODIFICADO", entidad="Pago", fecha_hora=now - timedelta(days=2), resultado="EXITOSO", detalles={}),
        AuditLog(organizacion_id=2, usuario_id=user_other.id_usuario, rol="ADMINISTRADOR", accion="PEDIDO_CREADO", entidad="Pedido", fecha_hora=now, resultado="EXITOSO", detalles={}),
    ])
    db.commit()
    from app.services.audit_service import AuditService
    total, items = AuditService.list_activity(db, 1, desde=now - timedelta(hours=1), tipo="PEDIDO_CREADO", usuario_id=user_one.id_usuario, limit=1, offset=0)
    assert total == 1
    assert len(items) == 1 and items[0].organizacion_id == 1
