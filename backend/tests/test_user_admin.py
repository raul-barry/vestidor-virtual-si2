from fastapi.testclient import TestClient
from sqlalchemy import select

from conftest import session_token
from app.main import app
from app.models.bitacora import Bitacora
from app.models.rol import Rol
from app.models.usuario import Usuario


def get_or_create_role(db, nombre: str) -> Rol:
    role = db.scalar(select(Rol).where(Rol.nombre == nombre))
    if role is None:
        role = Rol(nombre=nombre, descripcion=None)
        db.add(role)
        db.flush()
    return role


def create_user(db, role_name: str, correo: str, estado: str = "ACTIVO") -> Usuario:
    role = get_or_create_role(db, role_name)
    user = Usuario(
        id_rol=role.id_rol,
        nombres="Admin" if role_name == "ADMINISTRADOR" else "Cliente",
        apellidos="User",
        correo=correo,
        telefono="70000000",
        password_hash="hash",
        estado=estado,
    )
    db.add(user)
    db.commit()
    return user


def admin_headers(db) -> tuple[dict[str, str], Usuario]:
    admin = create_user(db, "ADMINISTRADOR", "admin@example.com")
    token = session_token(db, {"id_usuario": admin.id_usuario, "rol": "ADMINISTRADOR"})
    return {"Authorization": f"Bearer {token}"}, admin


def test_admin_can_list_and_get_user_detail(db) -> None:
    headers, _ = admin_headers(db)
    customer = create_user(db, "CLIENTE", "cliente@example.com")
    client = TestClient(app)

    listed = client.get("/api/admin/users", headers=headers)
    detail = client.get(f"/api/admin/users/{customer.id_usuario}", headers=headers)

    assert listed.status_code == 200
    assert len(listed.json()) == 2
    assert detail.status_code == 200
    assert detail.json()["correo"] == "cliente@example.com"
    assert detail.json()["rol"] == "CLIENTE"


def test_admin_can_change_user_status_and_register_audit(db) -> None:
    headers, admin = admin_headers(db)
    customer = create_user(db, "CLIENTE", "cliente@example.com")

    response = TestClient(app).put(
        f"/api/admin/users/{customer.id_usuario}/status",
        headers=headers,
        json={"estado": "INACTIVO"},
    )

    assert response.status_code == 200
    assert response.json()["estado"] == "INACTIVO"
    audit = db.scalar(select(Bitacora).where(Bitacora.id_usuario == admin.id_usuario))
    assert audit is not None
    assert audit.accion == f"Administrador {admin.id_usuario} cambió estado de usuario {customer.id_usuario}: ACTIVO -> INACTIVO"


def test_admin_can_change_another_users_role(db) -> None:
    headers, _ = admin_headers(db)
    customer = create_user(db, "CLIENTE", "cliente@example.com")
    cashier = get_or_create_role(db, "CAJERO")
    db.commit()

    response = TestClient(app).put(
        f"/api/admin/users/{customer.id_usuario}/role",
        headers=headers,
        json={"id_rol": cashier.id_rol},
    )

    assert response.status_code == 200
    assert response.json()["rol"] == "CAJERO"


def test_cannot_deactivate_last_administrator_or_change_current_admin_role(db) -> None:
    headers, admin = admin_headers(db)
    client_role = get_or_create_role(db, "CLIENTE")
    db.commit()
    client = TestClient(app)

    deactivate = client.put(
        f"/api/admin/users/{admin.id_usuario}/status",
        headers=headers,
        json={"estado": "INACTIVO"},
    )
    change_role = client.put(
        f"/api/admin/users/{admin.id_usuario}/role",
        headers=headers,
        json={"id_rol": client_role.id_rol},
    )

    assert deactivate.status_code == 422
    assert change_role.status_code == 422


def test_customer_cannot_access_user_administration(db) -> None:
    customer = create_user(db, "CLIENTE", "cliente@example.com")
    token = session_token(db, {"id_usuario": customer.id_usuario, "rol": "CLIENTE"})

    response = TestClient(app).get("/api/admin/users", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403
