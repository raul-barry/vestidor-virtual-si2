from fastapi.testclient import TestClient

from app.database.seed import seed_roles
from app.main import app
from app.models.cliente import Cliente
from app.models.usuario import Usuario


def register_payload(correo: str = "cliente@example.com") -> dict[str, str]:
    return {
        "nombres": "Carlos",
        "apellidos": "Perez",
        "correo": correo,
        "telefono": "70000000",
        "password": "password-seguro",
    }


def test_register_client_creates_user_client_and_assigns_client_role(db) -> None:
    seed_roles(db)
    db.commit()

    response = TestClient(app).post("/api/auth/register", json=register_payload())

    assert response.status_code == 201
    assert response.json() == {
        "id_usuario": 1,
        "nombres": "Carlos",
        "apellidos": "Perez",
        "correo": "cliente@example.com",
        "telefono": "70000000",
        "rol": "CLIENTE",
    }
    assert "password_hash" not in response.json()

    usuario = db.get(Usuario, 1)
    cliente = db.get(Cliente, 1)
    assert usuario is not None
    assert usuario.password_hash != "password-seguro"
    assert cliente is not None
    assert cliente.id_usuario == usuario.id_usuario
    assert usuario.rol.nombre == "CLIENTE"


def test_register_client_rejects_duplicate_email(db) -> None:
    seed_roles(db)
    db.commit()
    client = TestClient(app)

    first_response = client.post("/api/auth/register", json=register_payload())
    duplicate_response = client.post("/api/auth/register", json=register_payload())

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 400
    assert duplicate_response.json()["message"] == "El correo ya está registrado"


def test_register_endpoint_is_documented_in_openapi() -> None:
    operation = app.openapi()["paths"]["/api/auth/register"]["post"]

    assert "requestBody" in operation
    assert "201" in operation["responses"]
    assert "400" in operation["responses"]
