from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_api_starts_and_root_responds() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "API funcionando correctamente"}


def test_health_responds() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
