from fastapi.testclient import TestClient
from sqlalchemy import select

from conftest import session_token
from app.main import app
from app.models.bitacora import Bitacora
from app.models.rol import Rol
from app.models.usuario import Usuario
from app.models.sucursal import Sucursal


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
    branch = Sucursal(nombre="Sucursal Caja", direccion="Av. Caja", estado="ACTIVA")
    db.add(branch)
    db.commit()

    response = TestClient(app).put(
        f"/api/admin/users/{customer.id_usuario}/role",
        headers=headers,
        json={"id_rol": cashier.id_rol, "id_sucursal": branch.id_sucursal},
    )

    assert response.status_code == 200
    assert response.json()["rol"] == "CAJERO"
    assert response.json()["id_sucursal"] == branch.id_sucursal


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


def test_admin_completes_create_edit_branch_deactivate_and_restore_flow(db) -> None:
    headers, _ = admin_headers(db)
    cashier = get_or_create_role(db, "CAJERO")
    branch = Sucursal(nombre="Sucursal Centro", direccion="Av. Central 10", ciudad="La Paz", estado="ACTIVA")
    db.add(branch)
    db.commit()
    client = TestClient(app)

    created = client.post(
        "/api/admin/users",
        headers=headers,
        json={
            "nombres": "Carlos",
            "apellidos": "Caja",
            "correo": "carlos.caja@example.com",
            "telefono": "70000001",
            "password": "Seguro123!",
            "rol": cashier.nombre,
            "id_sucursal": branch.id_sucursal,
        },
    )
    assert created.status_code == 201, created.text
    user_id = created.json()["id_usuario"]
    assert created.json()["sucursal"] == "Sucursal Centro"

    updated = client.put(
        f"/api/admin/users/{user_id}",
        headers=headers,
        json={"nombres": "Carlos Editado", "telefono": "71111111", "id_sucursal": branch.id_sucursal},
    )
    assert updated.status_code == 200
    assert updated.json()["nombres"] == "Carlos Editado"
    assert updated.json()["id_sucursal"] == branch.id_sucursal

    disabled = client.put(
        f"/api/admin/users/{user_id}/status",
        headers=headers,
        json={"estado": "INACTIVO"},
    )
    restored = client.put(
        f"/api/admin/users/{user_id}/status",
        headers=headers,
        json={"estado": "ACTIVO"},
    )
    assert disabled.status_code == 200 and disabled.json()["estado"] == "INACTIVO"
    assert restored.status_code == 200 and restored.json()["estado"] == "ACTIVO"


def test_create_branch_manager_requires_and_receives_same_tenant_branch(db) -> None:
    headers, admin = admin_headers(db)
    manager = get_or_create_role(db, "ENCARGADO_SUCURSAL")
    branch = Sucursal(nombre="Sucursal Encargado", direccion="Av. Principal", estado="ACTIVA")
    db.add(branch)
    db.commit()
    client = TestClient(app)
    payload = {"nombres":"Ana", "apellidos":"Encargada", "correo":"ana.encargada@example.com",
               "password":"Seguro123!", "rol":manager.nombre}

    missing_branch = client.post("/api/admin/users", headers=headers, json=payload)
    assert missing_branch.status_code == 422

    created = client.post("/api/admin/users", headers=headers, json={**payload, "id_sucursal":branch.id_sucursal})
    assert created.status_code == 201, created.text
    assert created.json()["rol"] == "ENCARGADO_SUCURSAL"
    assert created.json()["id_sucursal"] == branch.id_sucursal
    assert db.get(Usuario, created.json()["id_usuario"]).id_organizacion == admin.id_organizacion


def test_company_admin_cannot_assign_foreign_branch_or_custom_global_role(db) -> None:
    headers, _ = admin_headers(db)
    manager = get_or_create_role(db, "ENCARGADO_SUCURSAL")
    custom = get_or_create_role(db, "CUSTOM_GLOBAL_ROLE")
    db.flush()
    db.info.pop("organization_id", None)
    from app.models.organizacion import Organizacion
    foreign_org = Organizacion(id_organizacion=2, nombre="Otra empresa", slug="otra-empresa", estado="ACTIVA")
    db.add(foreign_org)
    db.flush()
    foreign_branch = Sucursal(id_organizacion=2, nombre="Sucursal Externa", direccion="Otra dirección", estado="ACTIVA")
    db.add(foreign_branch)
    db.commit()
    db.info["organization_id"] = 1
    client = TestClient(app)
    payload = {"nombres":"Luis", "apellidos":"Prueba", "correo":"luis.prueba@example.com",
               "password":"Seguro123!", "rol":manager.nombre, "id_sucursal":foreign_branch.id_sucursal}

    foreign = client.post("/api/admin/users", headers=headers, json=payload)
    assert foreign.status_code == 422
    custom_role = client.post("/api/admin/users", headers=headers, json={**payload, "correo":"custom@example.com", "rol":custom.nombre, "id_sucursal":None})
    assert custom_role.status_code == 422


def test_company_admin_cannot_assign_platform_role(db) -> None:
    headers, _ = admin_headers(db)
    platform = get_or_create_role(db, "ADMINISTRADOR_PLATAFORMA")
    db.commit()
    response = TestClient(app).post("/api/admin/users", headers=headers, json={
        "nombres":"Platform", "apellidos":"Forbidden", "correo":"platform.forbidden@example.com",
        "password":"Seguro123!", "rol":platform.nombre,
    })
    assert response.status_code == 403
