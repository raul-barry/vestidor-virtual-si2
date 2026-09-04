from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.database.seed import seed_roles
from app.main import app
from app.models.bitacora import Bitacora
from app.models.sesion import Sesion


def register_payload() -> dict[str, str]:
    return {
        "nombres": "Carlos",
        "apellidos": "Perez",
        "correo": "cliente@example.com",
        "telefono": "70000000",
        "password": "password-seguro",
    }


def login_payload() -> dict[str, str]:
    return {"correo": "cliente@example.com", "password": "password-seguro"}


def create_logged_in_client(db, client: TestClient) -> tuple[int, str]:
    seed_roles(db)
    db.commit()
    registration = client.post("/api/auth/register", json=register_payload())
    assert registration.status_code == 201
    login = client.post("/api/auth/login", json=login_payload())
    assert login.status_code == 200
    return registration.json()["id_usuario"], login.json()["access_token"]


def test_logout_inactivates_session_and_creates_bitacora(db) -> None:
    client = TestClient(app)
    user_id, token = create_logged_in_client(db, client)

    response = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == {"message": "Sesión cerrada correctamente"}
    sesion = db.get(Sesion, 1)
    assert sesion is not None
    assert sesion.id_usuario == user_id
    assert sesion.estado == "INACTIVA"
    assert db.get(Bitacora, 1) is not None
    logout_bitacora = db.get(Bitacora, 2)
    assert logout_bitacora is not None
    assert logout_bitacora.accion == "Cierre de sesión"


def test_logout_rejects_invalid_token(db) -> None:
    response = TestClient(app).post(
        "/api/auth/logout", headers={"Authorization": "Bearer invalid-token"}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Token inválido"


def test_logout_rejects_user_without_active_session(db) -> None:
    client = TestClient(app)
    seed_roles(db)
    db.commit()
    registration = client.post("/api/auth/register", json=register_payload())
    user_id = registration.json()["id_usuario"]
    token = create_access_token({"id_usuario": user_id, "rol": "CLIENTE"})

    response = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 404
    assert response.json()["message"] == "Sesión no encontrada"


def test_logout_endpoint_is_documented_with_bearer_auth() -> None:
    operation = app.openapi()["paths"]["/api/auth/logout"]["post"]

    assert operation["security"]
    assert "200" in operation["responses"]
    assert "401" in operation["responses"]
    assert "404" in operation["responses"]
