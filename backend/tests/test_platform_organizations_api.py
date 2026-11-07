from fastapi.testclient import TestClient

from conftest import session_token
from app.main import app
from app.models.audit_log import AuditLog
from app.models.organizacion import Organizacion
from app.models.rol import Rol
from app.models.sucursal import Sucursal
from app.models.usuario import Usuario


def _user_headers(db, role_name: str, email: str, organization_id: int = 1) -> dict[str, str]:
    role = db.query(Rol).filter(Rol.nombre == role_name).one_or_none()
    if role is None:
        role = Rol(nombre=role_name, estado="ACTIVO")
        db.add(role)
        db.flush()
    user = Usuario(
        id_organizacion=organization_id,
        id_rol=role.id_rol,
        nombres="Ana",
        apellidos="Admin",
        correo=email,
        telefono="70000000",
        password_hash="sensitive-hash-must-not-be-returned",
        estado="ACTIVO",
    )
    db.add(user)
    db.commit()
    token = session_token(db, {"id_usuario": user.id_usuario, "rol": role_name})
    return {"Authorization": f"Bearer {token}"}


def _platform_headers(db) -> dict[str, str]:
    return _user_headers(db, "ADMINISTRADOR_PLATAFORMA", "platform@example.test")


def test_organization_suspend_reactivate_are_audited_without_duplicates(db):
    headers = _platform_headers(db)
    client = TestClient(app)
    suspended = client.patch("/api/platform/organizations/1/status", headers=headers, json={"estado": "INACTIVA"})
    repeated = client.patch("/api/platform/organizations/1/status", headers=headers, json={"estado": "INACTIVA"})
    reactivated = client.patch("/api/platform/organizations/1/status", headers=headers, json={"estado": "ACTIVA"})
    assert suspended.status_code == repeated.status_code == reactivated.status_code == 200
    assert suspended.json()["estado"] == repeated.json()["estado"] == "INACTIVA"
    assert reactivated.json()["estado"] == "ACTIVA"
    actions = db.query(AuditLog.accion).filter(AuditLog.organizacion_id == 1).all()
    assert [row[0] for row in actions].count("ORGANIZACION_SUSPENDIDA") == 1
    assert [row[0] for row in actions].count("ORGANIZACION_REACTIVADA") == 1


def test_create_get_and_update_full_organization_business_profile(db):
    headers = _platform_headers(db)
    client = TestClient(app)
    payload = {
        "nombre": "Casa Estilo",
        "razon_social": "Casa Estilo SRL",
        "nit": "123456789",
        "correo_contacto": "contacto@casaestilo.test",
        "telefono_contacto": "+591 70000000",
        "direccion": "Av. Central 321",
        "logo_url": "https://cdn.casaestilo.test/logo.png",
        "slug": "casa-estilo",
    }

    created = client.post("/api/platform/organizations", headers=headers, json=payload)
    assert created.status_code == 201, created.text
    organization_id = created.json()["id_organizacion"]
    assert {key: created.json()[key] for key in payload} == payload
    assert created.json()["fecha_creacion"]
    assert created.json()["fecha_actualizacion"]

    fetched = client.get(f"/api/platform/organizations/{organization_id}", headers=headers)
    before_update = fetched.json()["fecha_actualizacion"]
    updated = client.patch(f"/api/platform/organizations/{organization_id}", headers=headers,
                           json={"razon_social": "Casa Estilo Bolivia SRL", "direccion": None})

    assert fetched.status_code == 200
    assert updated.status_code == 200
    assert updated.json()["razon_social"] == "Casa Estilo Bolivia SRL"
    assert updated.json()["direccion"] is None
    assert updated.json()["fecha_actualizacion"] != before_update
    assert updated.json()["correo_contacto"] == "contacto@casaestilo.test"


def test_duplicate_nit_and_slug_are_rejected(db):
    db.add(Organizacion(id_organizacion=2, nombre="Existing Shop", slug="existing-shop", estado="ACTIVA", nit="123456789"))
    db.commit()
    headers = _platform_headers(db)
    client = TestClient(app)

    duplicate_nit = client.post("/api/platform/organizations", headers=headers,
                                json={"nombre": "New Shop", "slug": "new-shop", "nit": "123456789"})
    duplicate_slug = client.post("/api/platform/organizations", headers=headers,
                                 json={"nombre": "Different Shop", "slug": "existing-shop"})

    assert duplicate_nit.status_code == 409
    assert duplicate_slug.status_code == 409


def test_business_profile_formats_are_validated(db):
    headers = _platform_headers(db)
    client = TestClient(app)
    invalid_email = client.post("/api/platform/organizations", headers=headers,
                                json={"nombre": "Email Shop", "correo_contacto": "not-an-email"})
    invalid_phone = client.post("/api/platform/organizations", headers=headers,
                                json={"nombre": "Phone Shop", "telefono_contacto": "letters"})
    invalid_logo = client.post("/api/platform/organizations", headers=headers,
                               json={"nombre": "Logo Shop", "logo_url": "javascript:alert(1)"})

    assert invalid_email.status_code == 422
    assert invalid_phone.status_code == 422
    assert invalid_logo.status_code == 422


def test_platform_admin_reads_organization_branches_and_users_without_secrets(db):
    db.info.pop("organization_id", None)
    db.add(Organizacion(id_organizacion=2, nombre="Urban Vogue", slug="urban-vogue", estado="ACTIVA"))
    role = Rol(nombre="ENCARGADO_SUCURSAL", estado="ACTIVO")
    db.add(role)
    db.flush()
    branch = Sucursal(id_organizacion=2, nombre="Centro", direccion="Av. Central 10", ciudad="La Paz", estado="ACTIVA")
    db.add(branch)
    db.flush()
    user = Usuario(id_organizacion=2, id_sucursal=branch.id_sucursal, id_rol=role.id_rol,
                   nombres="Luis", apellidos="Rojas", correo="luis@urban.test",
                   password_hash="do-not-return-this-hash", estado="ACTIVO")
    db.add(user)
    db.commit()
    headers = _platform_headers(db)
    client = TestClient(app)

    listing = client.get("/api/platform/organizations", headers=headers)
    organization = client.get("/api/platform/organizations/2", headers=headers)
    branches = client.get("/api/platform/organizations/2/branches", headers=headers)
    users = client.get("/api/platform/organizations/2/users", headers=headers)

    assert listing.status_code == 200
    assert {row["id_organizacion"] for row in listing.json()} == {1, 2}
    assert organization.status_code == 200
    organization_data = organization.json()
    assert {key: value for key, value in organization_data.items() if not key.startswith("fecha_")} == {
        "id_organizacion": 2,
        "nombre": "Urban Vogue",
        "razon_social": None,
        "nit": None,
        "correo_contacto": None,
        "telefono_contacto": None,
        "direccion": None,
        "logo_url": None,
        "slug": "urban-vogue",
        "estado": "ACTIVA",
    }
    assert organization_data["fecha_creacion"]
    assert organization_data["fecha_actualizacion"]
    assert branches.status_code == 200
    assert branches.json() == [{"id_sucursal": branch.id_sucursal, "nombre": "Centro", "direccion": "Av. Central 10", "ciudad": "La Paz", "estado": "ACTIVA"}]
    assert users.status_code == 200
    assert users.json()[0]["nombre"] == "Luis Rojas"
    assert users.json()[0]["correo"] == "luis@urban.test"
    assert users.json()[0]["rol"] == "ENCARGADO_SUCURSAL"
    assert users.json()[0]["fecha_registro"]
    assert "password_hash" not in users.json()[0]
    assert "password" not in users.json()[0]
    assert "telefono" not in users.json()[0]
    assert "do-not-return-this-hash" not in users.text


def test_platform_admin_gets_empty_collections_for_organization_without_branches_or_users(db):
    db.add(Organizacion(id_organizacion=2, nombre="Empty Shop", slug="empty-shop", estado="ACTIVA"))
    db.commit()
    headers = _platform_headers(db)
    client = TestClient(app)

    assert client.get("/api/platform/organizations/2/branches", headers=headers).json() == []
    assert client.get("/api/platform/organizations/2/users", headers=headers).json() == []


def test_platform_organization_lookup_returns_404_for_unknown_id(db):
    response = TestClient(app).get("/api/platform/organizations/9876", headers=_platform_headers(db))
    assert response.status_code == 404


def test_platform_organization_endpoints_reject_company_admin_and_employee(db):
    client = TestClient(app)
    endpoints = (
        "/api/platform/organizations/1",
        "/api/platform/organizations/1/branches",
        "/api/platform/organizations/1/users",
    )
    company_admin = _user_headers(db, "ADMINISTRADOR", "company-admin@example.test")
    employee = _user_headers(db, "ENCARGADO_SUCURSAL", "employee@example.test")
    for headers in (company_admin, employee):
        for endpoint in endpoints:
            assert client.get(endpoint, headers=headers).status_code == 403


def test_platform_branch_and_user_lists_are_scoped_to_the_requested_organization(db):
    db.add(Organizacion(id_organizacion=2, nombre="Second Shop", slug="second-shop", estado="ACTIVA"))
    role = Rol(nombre="CAJERO", estado="ACTIVO")
    db.add(role)
    db.flush()
    branch = Sucursal(id_organizacion=1, nombre="Only One", direccion="Calle 1", ciudad="Santa Cruz", estado="ACTIVA")
    db.add(branch)
    db.flush()
    db.add(Usuario(id_organizacion=1, id_sucursal=branch.id_sucursal, id_rol=role.id_rol,
                   nombres="Test", apellidos="User", correo="one@example.test", password_hash="hash"))
    db.commit()
    headers = _platform_headers(db)
    client = TestClient(app)

    assert client.get("/api/platform/organizations/2/branches", headers=headers).json() == []
    assert client.get("/api/platform/organizations/2/users", headers=headers).json() == []


def test_user_assigned_to_another_organizations_branch_is_rejected(db):
    db.info.pop("organization_id", None)
    db.add(Organizacion(id_organizacion=2, nombre="Second Shop", slug="second-shop", estado="ACTIVA"))
    role = Rol(nombre="CAJERO", estado="ACTIVO")
    branch = Sucursal(id_organizacion=1, nombre="Main", direccion="Calle 1", ciudad="La Paz", estado="ACTIVA")
    db.add_all([role, branch])
    db.flush()
    db.add(Usuario(id_organizacion=2, id_sucursal=branch.id_sucursal, id_rol=role.id_rol,
                   nombres="Wrong", apellidos="Branch", correo="wrong-branch@example.test", password_hash="hash"))
    db.commit()

    response = TestClient(app).get("/api/platform/organizations/2/users", headers=_platform_headers(db))

    assert response.status_code == 409
