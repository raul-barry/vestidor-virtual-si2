from fastapi.testclient import TestClient

from app.core.security import verify_token
from app.database.seed import seed_roles
from app.main import app
from app.models.bitacora import Bitacora
from app.models.sesion import Sesion
from app.models.usuario import Usuario


def register_payload() -> dict[str, str]:
    return {
        "nombres": "Carlos",
        "apellidos": "Perez",
        "correo": "cliente@example.com",
        "telefono": "70000000",
        "password": "password-seguro",
    }


def login_payload(password: str = "password-seguro") -> dict[str, str]:
    return {"correo": "cliente@example.com", "password": password}


def create_registered_client(db, client: TestClient) -> int:
    seed_roles(db)
    db.commit()
    response = client.post("/api/auth/register", json=register_payload())
    assert response.status_code == 201
    return response.json()["id_usuario"]


def test_login_creates_token_session_and_bitacora(db) -> None:
    client = TestClient(app)
    user_id = create_registered_client(db, client)

    response = client.post("/api/auth/login", json=login_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["usuario"] == {"id_usuario": user_id, "correo": "cliente@example.com"}
    assert body["rol"] == "CLIENTE"
    assert "password_hash" not in body
    token_payload = verify_token(body["access_token"])
    assert token_payload is not None
    assert token_payload["id_usuario"] == user_id
    assert token_payload["rol"] == "CLIENTE"
    assert "exp" in token_payload

    sesion = db.get(Sesion, 1)
    bitacora = db.get(Bitacora, 1)
    assert sesion is not None
    assert sesion.id_usuario == user_id
    assert sesion.token_jwt == body["access_token"]
    assert sesion.estado == "ACTIVA"
    assert bitacora is not None
    assert bitacora.id_usuario == user_id
    assert bitacora.accion == "Inicio de sesión"


def test_login_rejects_unknown_email(db) -> None:
    response = TestClient(app).post("/api/auth/login", json=login_payload())

    assert response.status_code == 401
    assert response.json()["message"] == "Credenciales inválidas"


def test_login_rejects_invalid_password(db) -> None:
    client = TestClient(app)
    create_registered_client(db, client)

    response = client.post("/api/auth/login", json=login_payload("incorrecta"))

    assert response.status_code == 401
    assert response.json()["message"] == "Credenciales inválidas"


def test_login_rejects_inactive_user(db) -> None:
    client = TestClient(app)
    user_id = create_registered_client(db, client)
    usuario = db.get(Usuario, user_id)
    assert usuario is not None
    usuario.estado = "INACTIVO"
    db.commit()

    response = client.post("/api/auth/login", json=login_payload())

    assert response.status_code == 403
    assert response.json()["message"] == "Usuario inactivo"


def test_login_endpoint_is_documented_in_openapi() -> None:
    operation = app.openapi()["paths"]["/api/auth/login"]["post"]

    assert "requestBody" in operation
    assert "200" in operation["responses"]
    assert "401" in operation["responses"]
    assert "403" in operation["responses"]
