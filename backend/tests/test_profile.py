from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database.seed import seed_roles
from app.main import app
from app.models.bitacora import Bitacora
from app.models.cliente import Cliente
from app.models.usuario import Usuario


def register_payload() -> dict[str, str]:
    return {
        "nombres": "Carlos",
        "apellidos": "Perez",
        "correo": "cliente@example.com",
        "telefono": "70000000",
        "password": "password-seguro",
    }


def authenticated_client(db) -> tuple[TestClient, int, dict[str, str]]:
    seed_roles(db)
    db.commit()
    client = TestClient(app)
    registration = client.post("/api/auth/register", json=register_payload())
    assert registration.status_code == 201
    login = client.post(
        "/api/auth/login", json={"correo": "cliente@example.com", "password": "password-seguro"}
    )
    assert login.status_code == 200
    return client, registration.json()["id_usuario"], {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_get_profile_returns_authenticated_client_data(db) -> None:
    client, user_id, headers = authenticated_client(db)

    response = client.get("/api/users/profile", headers=headers)

    assert response.status_code == 200
    assert response.json() == {
        "id_usuario": user_id,
        "nombres": "Carlos",
        "apellidos": "Perez",
        "correo": "cliente@example.com",
        "telefono": "70000000",
    }
    assert "password_hash" not in response.json()


def test_update_profile_updates_allowed_fields_and_registers_bitacora(db) -> None:
    client, user_id, headers = authenticated_client(db)

    response = client.put(
        "/api/users/profile",
        headers=headers,
        json={"nombres": "Carlos Alberto", "telefono": "79999999"},
    )

    assert response.status_code == 200
    assert response.json()["nombres"] == "Carlos Alberto"
    assert response.json()["telefono"] == "79999999"
    usuario = db.get(Usuario, user_id)
    assert usuario is not None
    db.refresh(usuario)
    assert usuario.nombres == "Carlos Alberto"
    assert usuario.telefono == "79999999"
    cliente = db.get(Cliente, 1)
    assert cliente is not None
    assert cliente.id_usuario == user_id
    assert list(db.scalars(select(Bitacora.accion).order_by(Bitacora.nro_bitacora))) == [
        "Inicio de sesión",
        "Actualización de perfil",
    ]


def test_profile_rejects_invalid_token(db) -> None:
    response = TestClient(app).get(
        "/api/users/profile", headers={"Authorization": "Bearer invalid-token"}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Token inválido"


def test_profile_rejects_email_and_role_changes(db) -> None:
    client, user_id, headers = authenticated_client(db)

    role_response = client.put(
        "/api/users/profile", headers=headers, json={"nombres": "Otro", "rol": "ADMINISTRADOR"}
    )
    email_response = client.put(
        "/api/users/profile", headers=headers, json={"correo": "otro@example.com"}
    )

    assert role_response.status_code == 422
    assert email_response.status_code == 422
    usuario = db.get(Usuario, user_id)
    assert usuario is not None
    assert usuario.correo == "cliente@example.com"


def test_profile_endpoints_are_documented_with_bearer_auth() -> None:
    paths = app.openapi()["paths"]
    get_operation = paths["/api/users/profile"]["get"]
    update_operation = paths["/api/users/profile"]["put"]

    assert get_operation["security"]
    assert "200" in get_operation["responses"]
    assert update_operation["security"]
    assert "requestBody" in update_operation
    assert "200" in update_operation["responses"]
