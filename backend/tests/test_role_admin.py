from fastapi.testclient import TestClient
from sqlalchemy import select

from conftest import session_token
from app.main import app
from app.models.rol import Permiso, Rol
from app.models.usuario import Usuario


def headers(db, role_name: str = "ADMINISTRADOR_PLATAFORMA", email: str = "platform-roles@example.com"):
    if role_name == "ADMINISTRADOR_PLATAFORMA":
        db.info.pop("organization_id", None)
    role = db.scalar(select(Rol).where(Rol.nombre == role_name))
    if role is None:
        role = Rol(nombre=role_name, descripcion="Test role", estado="ACTIVO")
        db.add(role)
        db.flush()
    user = Usuario(
        id_organizacion=None if role_name == "ADMINISTRADOR_PLATAFORMA" else 1,
        id_rol=role.id_rol,
        nombres="Admin",
        apellidos="Test",
        correo=email,
        password_hash="hash",
        estado="ACTIVO",
    )
    db.add(user)
    db.commit()
    token = session_token(db, {"id_usuario": user.id_usuario, "rol": role_name})
    return {"Authorization": f"Bearer {token}"}


def test_platform_admin_can_manage_global_roles_and_base_roles_are_protected(db):
    client = TestClient(app)
    auth = headers(db)
    db.add(Rol(nombre="ADMINISTRADOR", descripcion="Base", estado="ACTIVO"))
    db.add(Permiso(codigo="CATALOGO_GESTIONAR", descripcion="Catalog management"))
    db.commit()

    permissions = client.get("/api/admin/roles/permissions", headers=auth).json()
    assert permissions
    created = client.post(
        "/api/admin/roles",
        headers=auth,
        json={"nombre": "EDITOR", "descripcion": "Editor", "permisos": [permissions[0]["id_permiso"]]},
    )
    assert created.status_code == 201
    assert created.json()["permisos"][0]["codigo"] == permissions[0]["codigo"]

    toggled = client.patch(f"/api/admin/roles/{created.json()['id_rol']}/toggle-status", headers=auth)
    assert toggled.status_code == 200 and toggled.json()["estado"] == "INACTIVO"
    restored = client.patch(f"/api/admin/roles/{created.json()['id_rol']}/toggle-status", headers=auth)
    assert restored.status_code == 200 and restored.json()["estado"] == "ACTIVO"
    edited = client.put(
        f"/api/admin/roles/{created.json()['id_rol']}",
        headers=auth,
        json={"nombre": "EDITOR", "descripcion": "Sin permisos", "permisos": []},
    )
    assert edited.status_code == 200 and edited.json()["permisos"] == []

    base = next(role for role in client.get("/api/admin/roles", headers=auth).json() if role["nombre"] == "ADMINISTRADOR")
    assert client.patch(f"/api/admin/roles/{base['id_rol']}/toggle-status", headers=auth).status_code == 422
    base_updated = client.put(
        f"/api/admin/roles/{base['id_rol']}",
        headers=auth,
        json={"nombre": "ADMINISTRADOR", "descripcion": "Rol base protegido", "permisos": [permissions[0]["id_permiso"]]},
    )
    assert base_updated.status_code == 200 and base_updated.json()["permisos"]
    assert client.put(
        f"/api/admin/roles/{base['id_rol']}",
        headers=auth,
        json={"nombre": "SUPERADMIN", "descripcion": "No permitido", "permisos": []},
    ).status_code == 422


def test_company_admin_employee_and_client_cannot_read_or_change_global_roles(db):
    client = TestClient(app)
    for index, role_name in enumerate(("ADMINISTRADOR", "ENCARGADO_SUCURSAL", "CAJERO", "CLIENTE")):
        auth = headers(db, role_name, f"{role_name.lower()}-{index}@roles.test")
        assert client.get("/api/admin/roles", headers=auth).status_code == 403
        assert client.get("/api/admin/roles/permissions", headers=auth).status_code == 403
        assert client.post(
            "/api/admin/roles",
            headers=auth,
            json={"nombre": "LOCAL_EDITOR", "descripcion": "No global", "permisos": []},
        ).status_code == 403
        assert client.put(
            "/api/admin/roles/1",
            headers=auth,
            json={"nombre": "ADMINISTRADOR", "descripcion": "No global", "permisos": []},
        ).status_code == 403
        assert client.patch("/api/admin/roles/1/toggle-status", headers=auth).status_code == 403


def test_company_admin_can_load_assignable_roles_without_platform_admin(db):
    client = TestClient(app)
    auth = headers(db, "ADMINISTRADOR", "company-roles-list@example.com")
    db.add_all([
        Rol(nombre="CLIENTE", descripcion="Cliente", estado="ACTIVO"),
        Rol(nombre="CAJERO", descripcion="Caja", estado="ACTIVO"),
        Rol(nombre="INACTIVO_TEST", descripcion="Inactivo", estado="INACTIVO"),
        Rol(nombre="ADMINISTRADOR_PLATAFORMA", descripcion="Plataforma", estado="ACTIVO"),
    ])
    db.commit()

    response = client.get("/api/admin/users/roles", headers=auth)

    assert response.status_code == 200
    names = {role["nombre"] for role in response.json()}
    assert {"CLIENTE", "CAJERO"} <= names
    assert "INACTIVO_TEST" not in names
    assert "ADMINISTRADOR_PLATAFORMA" not in names


def test_company_role_catalog_excludes_platform_custom_and_inactive_roles(db):
    client = TestClient(app)
    auth = headers(db, "ADMINISTRADOR", "company-role-catalog@example.com")
    db.add_all([
        Rol(nombre="CLIENTE", descripcion="Cliente", estado="ACTIVO"),
        Rol(nombre="ENCARGADO_SUCURSAL", descripcion="Encargado", estado="ACTIVO"),
        Rol(nombre="CUSTOM_PLATFORM_ROLE", descripcion="Global", estado="ACTIVO"),
        Rol(nombre="INACTIVE_COMPANY_ROLE", descripcion="Inactivo", estado="INACTIVO"),
        Rol(nombre="ADMINISTRADOR_PLATAFORMA", descripcion="Plataforma", estado="ACTIVO"),
    ])
    db.commit()

    response = client.get("/api/admin/users/roles", headers=auth)

    assert response.status_code == 200
    names = {role["nombre"] for role in response.json()}
    assert names == {"ADMINISTRADOR", "CLIENTE", "ENCARGADO_SUCURSAL"}


def test_only_company_administrator_can_read_assignable_role_catalog(db):
    client = TestClient(app)
    for index, role_name in enumerate(("CLIENTE", "ENCARGADO_SUCURSAL", "CAJERO")):
        auth = headers(db, role_name, f"not-admin-role-catalog-{index}@example.test")
        assert client.get("/api/admin/users/roles", headers=auth).status_code == 403
