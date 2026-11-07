from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select, text

from conftest import session_token
from app.main import app
from app.models.rol import Rol
from app.models.sync_idempotency import SyncIdempotency
from app.models.usuario import Usuario
from app.services.sync_handlers import SyncHandlerError, sync_handlers


def _auth(db, email: str, organization: int = 1):
    role = db.scalar(select(Rol).where(Rol.nombre == "ADMINISTRADOR"))
    if role is None:
        role = Rol(nombre="ADMINISTRADOR", estado="ACTIVO")
        db.add(role)
        db.flush()
    user = Usuario(id_organizacion=organization, id_rol=role.id_rol,
                   nombres="Sync", apellidos="Test", correo=email,
                   password_hash="not-a-real-password", estado="ACTIVO")
    db.add(user)
    db.commit()
    token = session_token(db, {"id_usuario": user.id_usuario, "rol": "ADMINISTRADOR"})
    return {"Authorization": f"Bearer {token}"}


def _operation(*, operation_uuid=None, tenant_scope="org:1", payload=None, operation_type="not_implemented"):
    return {
        "operation_uuid": str(operation_uuid or uuid4()),
        "operation_type": operation_type,
        "payload": payload or {"value": 1},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": 1,
        "client_id": "test-device-1",
        "tenant_scope": tenant_scope,
    }


def test_sync_records_uuid_once_and_replays_result_without_repeating_handler(db):
    calls = []
    sync_handlers.register("test_noop", lambda _db, _actor, payload: calls.append(payload) or {"accepted": True})
    headers = _auth(db, "sync-idempotency@example.test")
    client = TestClient(app)
    operation = _operation(operation_type="test_noop")

    first = client.post("/api/sync/batch", headers=headers, json={"operations": [operation]})
    second = client.post("/api/sync/batch", headers=headers, json={"operations": [operation]})

    assert first.status_code == 200
    assert first.json()["results"][0]["status"] == "SINCRONIZADA"
    assert second.status_code == 200
    assert second.json()["results"][0]["duplicate"] is True
    assert second.json()["results"][0]["result"] == {"accepted": True}
    assert calls == [operation["payload"]]
    assert db.scalar(select(func.count()).select_from(SyncIdempotency)) == 1


def test_sync_rejects_reused_uuid_with_different_content_as_conflict(db):
    headers = _auth(db, "sync-conflict@example.test")
    client = TestClient(app)
    operation = _operation()
    assert client.post("/api/sync/batch", headers=headers, json={"operations": [operation]}).status_code == 200
    changed = {**operation, "payload": {"value": 2}}

    response = client.post("/api/sync/batch", headers=headers, json={"operations": [changed]})

    assert response.status_code == 409
    assert response.json()["results"][0]["category"] == "UUID_REUTILIZADO"
    assert db.scalar(select(func.count()).select_from(SyncIdempotency)) == 1


def test_sync_scope_comes_from_jwt_and_other_tenant_cannot_claim_operation(db):
    from app.models.organizacion import Organizacion
    db.info.pop("organization_id", None)
    db.add(Organizacion(id_organizacion=2, nombre="Otra empresa", slug="otra-empresa", estado="ACTIVA"))
    db.commit()
    headers = _auth(db, "sync-tenant-two@example.test", 2)
    response = TestClient(app).post("/api/sync/batch", headers=headers,
                                    json={"operations": [_operation(tenant_scope="org:1")]})

    assert response.status_code == 403
    assert response.json()["results"][0]["category"] == "NO_AUTORIZADA"
    assert db.scalar(select(func.count()).select_from(SyncIdempotency)) == 0


def test_sync_allows_same_uuid_in_distinct_organizations(db):
    from app.models.organizacion import Organizacion
    db.info.pop("organization_id", None)
    db.add(Organizacion(id_organizacion=2, nombre="Empresa dos", slug="empresa-dos", estado="ACTIVA"))
    db.commit()
    client = TestClient(app)
    first = _auth(db, "sync-org-one@example.test", 1)
    second = _auth(db, "sync-org-two@example.test", 2)
    operation_uuid = uuid4()

    one = client.post("/api/sync/batch", headers=first,
                      json={"operations": [_operation(operation_uuid=operation_uuid, tenant_scope="org:1")]})
    two = client.post("/api/sync/batch", headers=second,
                      json={"operations": [_operation(operation_uuid=operation_uuid, tenant_scope="org:2")]})

    assert one.status_code == two.status_code == 200
    assert db.scalar(select(func.count()).select_from(SyncIdempotency).where(
        SyncIdempotency.operation_uuid == str(operation_uuid)
    )) == 2


def test_sync_returns_individual_results_for_partial_batch(db):
    sync_handlers.register("test_partial_success", lambda _db, _actor, _payload: {"accepted": True})
    headers = _auth(db, "sync-partial@example.test")
    operations = [_operation(operation_type="test_partial_success"), _operation(operation_type="also_not_implemented")]

    response = TestClient(app).post("/api/sync/batch", headers=headers, json={"operations": operations})

    assert response.status_code == 200
    assert [item["status"] for item in response.json()["results"]] == ["SINCRONIZADA", "RECHAZADA"]
    assert response.json()["results"][1]["category"] == "OPERACION_NO_IMPLEMENTADA"


def test_sync_retries_transient_handler_error_then_persists_success(db):
    attempts = []
    db.execute(text("CREATE TABLE sync_test_effects (value INTEGER NOT NULL)"))
    db.commit()

    def flaky(handler_db, _actor, _payload):
        attempts.append(True)
        handler_db.execute(text("INSERT INTO sync_test_effects(value) VALUES (1)"))
        if len(attempts) == 1:
            raise SyncHandlerError("Temporal", "TEMPORAL", retryable=True)
        return {"done": True}

    sync_handlers.register("test_flaky", flaky)
    headers = _auth(db, "sync-retry@example.test")
    operation = _operation(operation_type="test_flaky")
    client = TestClient(app)

    failed = client.post("/api/sync/batch", headers=headers, json={"operations": [operation]})
    assert failed.json()["results"][0]["status"] == "ERROR_REINTENTABLE"
    assert db.scalar(text("SELECT COUNT(*) FROM sync_test_effects")) == 0

    retried = client.post("/api/sync/batch", headers=headers, json={"operations": [operation]})
    assert retried.json()["results"][0]["status"] == "SINCRONIZADA"
    assert db.scalar(text("SELECT COUNT(*) FROM sync_test_effects")) == 1
    assert attempts == [True, True]
    db.execute(text("DROP TABLE sync_test_effects"))
    db.commit()


def test_sync_rejects_invalid_uuid_before_processing_batch(db):
    headers = _auth(db, "sync-invalid@example.test")
    operation = _operation()
    operation["operation_uuid"] = "not-a-uuid"

    response = TestClient(app).post("/api/sync/batch", headers=headers, json={"operations": [operation]})

    assert response.status_code == 422
    assert db.scalar(select(func.count()).select_from(SyncIdempotency)) == 0
