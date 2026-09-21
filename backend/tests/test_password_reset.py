from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.security import verify_password
from app.database.seed import seed_roles
from app.main import app
from app.models.bitacora import Bitacora
from app.models.token_recuperacion import TokenRecuperacion
from app.models.usuario import Usuario
from app.core.config import settings


def register_payload() -> dict[str, str]:
    return {
        "nombres": "Carlos",
        "apellidos": "Perez",
        "correo": "cliente@example.com",
        "telefono": "70000000",
        "password": "password-original",
    }


def create_registered_client(db, client: TestClient) -> int:
    seed_roles(db)
    db.commit()
    response = client.post("/api/auth/register", json=register_payload())
    assert response.status_code == 201
    return response.json()["id_usuario"]


def request_reset(client: TestClient) -> str:
    response = client.post("/api/auth/request-password-reset", json={"correo": "cliente@example.com"})
    assert response.status_code == 200
    assert response.json()["message"] == "Solicitud de recuperación generada correctamente"
    return response.json()["token"]


def test_reset_password_updates_hash_and_marks_token_as_used(db) -> None:
    client = TestClient(app)
    user_id = create_registered_client(db, client)
    token_value = request_reset(client)
    recovery_token = db.get(TokenRecuperacion, 1)
    assert recovery_token is not None
    assert recovery_token.token == token_value
    assert not recovery_token.usado

    response = client.post(
        "/api/auth/reset-password",
        json={"token": token_value, "nueva_password": "password-nueva"},
    )

    assert response.status_code == 200
    assert response.json() == {"message": "Contraseña actualizada correctamente"}
    usuario = db.get(Usuario, user_id)
    assert usuario is not None
    db.refresh(usuario)
    db.refresh(recovery_token)
    assert usuario.password_hash != "password-nueva"
    assert verify_password("password-nueva", usuario.password_hash)
    assert recovery_token.usado
    assert [
        action for action in db.scalars(select(Bitacora.accion).order_by(Bitacora.nro_bitacora))
    ] == ["Solicitud de recuperación de contraseña", "Restablecimiento de contraseña"]


def test_request_reset_rejects_unknown_email(db) -> None:
    response = TestClient(app).post(
        "/api/auth/request-password-reset", json={"correo": "inexistente@example.com"}
    )

    assert response.status_code == 404
    assert response.json()["message"] == "Usuario no encontrado"


def test_reset_password_rejects_invalid_token(db) -> None:
    response = TestClient(app).post(
        "/api/auth/reset-password",
        json={"token": "invalid-token", "nueva_password": "password-nueva"},
    )

    assert response.status_code == 400
    assert response.json()["message"] == "Token de recuperación inválido o expirado"


def test_reset_password_rejects_expired_token(db) -> None:
    client = TestClient(app)
    create_registered_client(db, client)
    token_value = request_reset(client)
    recovery_token = db.get(TokenRecuperacion, 1)
    assert recovery_token is not None
    recovery_token.fecha_expiracion = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()

    response = client.post(
        "/api/auth/reset-password",
        json={"token": token_value, "nueva_password": "password-nueva"},
    )

    assert response.status_code == 400
    assert response.json()["message"] == "Token de recuperación inválido o expirado"


def test_reset_password_rejects_used_token(db) -> None:
    client = TestClient(app)
    create_registered_client(db, client)
    token_value = request_reset(client)
    recovery_token = db.get(TokenRecuperacion, 1)
    assert recovery_token is not None
    recovery_token.usado = True
    db.commit()

    response = client.post(
        "/api/auth/reset-password",
        json={"token": token_value, "nueva_password": "password-nueva"},
    )

    assert response.status_code == 400
    assert response.json()["message"] == "Token de recuperación inválido o expirado"


def test_password_reset_endpoints_are_documented_in_openapi() -> None:
    paths = app.openapi()["paths"]
    request_operation = paths["/api/auth/request-password-reset"]["post"]
    reset_operation = paths["/api/auth/reset-password"]["post"]

    assert "requestBody" in request_operation
    assert "200" in request_operation["responses"]
    assert "404" in request_operation["responses"]
    assert "requestBody" in reset_operation
    assert "200" in reset_operation["responses"]
    assert "400" in reset_operation["responses"]


def test_request_reset_sends_email_and_does_not_expose_token(db, monkeypatch) -> None:
    client = TestClient(app)
    create_registered_client(db, client)

    class FakeSMTP:
        sent = None

        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def starttls(self):
            pass

        def login(self, username, password):
            self.credentials = (username, password)

        def send_message(self, message):
            FakeSMTP.sent = message

    monkeypatch.setattr(settings, "smtp_host", "smtp.example.test")
    monkeypatch.setattr(settings, "smtp_port", 587)
    monkeypatch.setattr(settings, "smtp_from", "no-reply@example.test")
    monkeypatch.setattr(settings, "smtp_username", "smtp-user")
    monkeypatch.setattr(settings, "smtp_password", "smtp-password")
    monkeypatch.setattr(settings, "smtp_starttls", True)
    monkeypatch.setattr("app.services.auth_service.smtplib.SMTP", FakeSMTP)

    response = client.post("/api/auth/request-password-reset", json={"correo": "cliente@example.com"})

    assert response.status_code == 200
    assert "token" not in response.json()
    assert FakeSMTP.sent is not None
    assert "Token de recuperación:" in FakeSMTP.sent.get_content()
