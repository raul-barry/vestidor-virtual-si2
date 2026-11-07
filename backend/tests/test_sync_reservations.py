from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.database.seed import seed_initial_data
from app.main import app
from app.models.inventario import Inventario
from app.models.movimiento_inventario import MovimientoInventario
from app.models.reserva import Reserva
from app.models.usuario import Usuario
from app.services.sync_handlers import sync_handlers
from conftest import session_token


def _client(db):
    seed_initial_data(db)
    db.commit()
    user = db.scalar(select(Usuario).where(Usuario.correo == "cliente@vestidor.local"))
    token = session_token(db, {"id_usuario": user.id_usuario, "rol": "CLIENTE"})
    return TestClient(app), user, {"Authorization": f"Bearer {token}"}


def _operation(user, kind, payload, *, operation_uuid=None, client_id="reservation-device"):
    return {
        "operation_uuid": str(operation_uuid or uuid4()),
        "operation_type": kind,
        "payload": {**payload, "id_usuario": user.id_usuario},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": 1,
        "client_id": client_id,
        "tenant_scope": f"org:{user.id_organizacion}",
    }


def test_offline_reservation_is_idempotent_and_uses_server_confirmation_time(db):
    client, user, headers = _client(db)
    inventory = db.scalar(select(Inventario).where(Inventario.stock_disponible > 0))
    original_stock = inventory.stock_disponible
    original = inventory.stock_disponible
    operation = _operation(user, "reserva.crear", {"id_inventario": inventory.id_inventario, "cantidad": 1})

    first = client.post("/api/sync/batch", headers=headers, json={"operations": [operation]})
    replay = client.post("/api/sync/batch", headers=headers, json={"operations": [operation]})

    result = first.json()["results"][0]
    assert result["status"] == "SINCRONIZADA"
    assert result["result"]["id_reserva"] > 0
    assert result["result"]["estado"] == "PENDIENTE"
    assert result["result"]["fecha_confirmacion_servidor"]
    assert result["result"]["fecha_expiracion_servidor"]
    assert replay.json()["results"][0]["duplicate"] is True
    assert db.scalar(select(Reserva).where(Reserva.id_reserva == result["result"]["id_reserva"])) is not None
    db.refresh(inventory)
    assert (inventory.stock_disponible, inventory.stock_reservado) == (original - 1, 1)


def test_two_offline_clients_compete_for_last_unit_and_second_is_rejected(db):
    client, user, headers = _client(db)
    inventory = db.scalar(select(Inventario).where(Inventario.stock_disponible > 0))
    inventory.stock_disponible = 1
    db.commit()
    first = _operation(user, "reserva.crear", {"id_inventario": inventory.id_inventario, "cantidad": 1}, client_id="device-a")
    second = _operation(user, "reserva.crear", {"id_inventario": inventory.id_inventario, "cantidad": 1}, client_id="device-b")

    response = client.post("/api/sync/batch", headers=headers, json={"operations": [first, second]})

    results = response.json()["results"]
    assert [item["status"] for item in results] == ["SINCRONIZADA", "RECHAZADA"]
    assert results[1]["category"] == "CONFLICTO_INVENTARIO"
    db.refresh(inventory)
    assert (inventory.stock_disponible, inventory.stock_reservado) == (0, 1)


def test_offline_cancellation_releases_stock_once_and_rejects_foreign_owner(db):
    client, user, headers = _client(db)
    inventory = db.scalar(select(Inventario).where(Inventario.stock_disponible > 0))
    original_stock = inventory.stock_disponible
    create = _operation(user, "reserva.crear", {"id_inventario": inventory.id_inventario, "cantidad": 1})
    created = client.post("/api/sync/batch", headers=headers, json={"operations": [create]}).json()["results"][0]["result"]
    cancel = _operation(user, "reserva.cancelar", {"id_reserva": created["id_reserva"]})
    cancelled = client.post("/api/sync/batch", headers=headers, json={"operations": [cancel]}).json()["results"][0]
    again = client.post("/api/sync/batch", headers=headers, json={"operations": [_operation(user, "reserva.cancelar", {"id_reserva": created["id_reserva"]})]}).json()["results"][0]

    assert cancelled["status"] == "SINCRONIZADA"
    assert cancelled["result"]["estado"] == "CANCELADA"
    assert again["status"] == "SINCRONIZADA"
    assert again["result"]["already_processed"] is True
    db.refresh(inventory)
    assert inventory.stock_reservado == 0
    assert inventory.stock_disponible == original_stock
    assert db.scalar(select(func.count()).select_from(MovimientoInventario).where(
        MovimientoInventario.tipo_movimiento == "LIBERACION_RESERVA"
    )) == 1


def test_limited_device_credential_only_syncs_reservations_and_can_be_revoked(db):
    client, user, headers = _client(db)
    credential = client.post("/api/sync/device-credentials", headers=headers, json={"client_id": "reservation-device"})
    assert credential.status_code == 200
    limited = {"Authorization": f"Bearer {credential.json()['sync_token']}"}
    inventory = db.scalar(select(Inventario).where(Inventario.stock_disponible > 0))
    operation = _operation(user, "reserva.crear", {"id_inventario": inventory.id_inventario, "cantidad": 1})

    accepted = client.post("/api/sync/batch", headers=limited, json={"operations": [operation]})
    forbidden = client.post("/api/sync/batch", headers=limited, json={"operations": [_operation(user, "other.operation", {})]})
    revoked = client.delete(f"/api/sync/device-credentials/{credential.json()['credential_id']}", headers=headers)
    after_revocation = client.post("/api/sync/batch", headers=limited, json={"operations": [operation]})

    assert accepted.status_code == 200
    assert forbidden.status_code == 403
    assert revoked.status_code == 200
    assert after_revocation.status_code == 401
