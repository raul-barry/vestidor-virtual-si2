from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.database.seed import seed_initial_data
from app.main import app
from app.models.inventario import Inventario
from app.models.movimiento_inventario import MovimientoInventario
from app.models.pago import Pago
from app.models.pedido import Pedido
from app.models.pedido_detalle import PedidoDetalle
from app.models.usuario import Usuario
from conftest import session_token


def _setup(db):
    seed_initial_data(db)
    db.commit()
    cashier = db.scalar(select(Usuario).where(Usuario.correo == "cajero@vestidor.local"))
    inventory = db.scalar(select(Inventario).where(Inventario.stock_disponible > 0))
    cashier.id_sucursal = inventory.id_sucursal
    db.commit()
    token = session_token(db, {"id_usuario": cashier.id_usuario, "rol": "CAJERO"})
    return TestClient(app), cashier, inventory, {"Authorization": f"Bearer {token}"}


def _op(user, inventory, *, operation_uuid=None, amount="999.00"):
    return {
        "operation_uuid": str(operation_uuid or uuid4()), "operation_type": "pos.venta_contado",
        "payload": {"id_sucursal": inventory.id_sucursal, "id_cliente": None,
                    "lineas": [{"id_variante": inventory.id_variante, "cantidad": 1}],
                    "importe_recibido": amount},
        "created_at": datetime.now(timezone.utc).isoformat(), "schema_version": 1,
        "client_id": "pos-terminal", "tenant_scope": f"org:{user.id_organizacion}",
    }


def test_offline_pos_cash_sale_is_idempotent_and_consumes_stock_once(db):
    client, cashier, inventory, headers = _setup(db)
    original_stock = inventory.stock_disponible
    operation = _op(cashier, inventory)
    first = client.post("/api/sync/batch", headers=headers, json={"operations": [operation]})
    replay = client.post("/api/sync/batch", headers=headers, json={"operations": [operation]})
    result = first.json()["results"][0]
    assert first.status_code == replay.status_code == 200
    assert result["status"] == "SINCRONIZADA"
    assert result["result"]["metodo_pago"] == "EFECTIVO"
    assert replay.json()["results"][0]["duplicate"] is True
    assert db.scalar(select(func.count()).select_from(Pedido)) == 1
    assert db.scalar(select(func.count()).select_from(Pago)) == 1
    assert db.scalar(select(func.count()).select_from(PedidoDetalle)) == 1
    db.refresh(inventory)
    assert inventory.stock_disponible == original_stock - 1
    assert db.scalar(select(func.count()).select_from(MovimientoInventario).where(
        MovimientoInventario.motivo.like("Venta presencial offline pedido %")
    )) == 1


def test_offline_pos_rejects_insufficient_cash_without_creating_order(db):
    client, cashier, inventory, headers = _setup(db)
    result = client.post("/api/sync/batch", headers=headers,
                         json={"operations": [_op(cashier, inventory, amount="0.01")]})
    assert result.json()["results"][0]["status"] == "RECHAZADA"
    assert db.scalar(select(func.count()).select_from(Pedido)) == 0
    assert db.scalar(select(func.count()).select_from(Pago)) == 0


def test_limited_cashier_device_credential_can_sync_only_pos_cash_sales(db):
    client, cashier, inventory, headers = _setup(db)
    credential = client.post("/api/sync/device-credentials", headers=headers, json={"client_id": "pos-terminal"})
    assert credential.status_code == 200
    device_headers = {"Authorization": f"Bearer {credential.json()['sync_token']}"}
    result = client.post("/api/sync/batch", headers=device_headers,
                         json={"operations": [_op(cashier, inventory)]})
    assert result.json()["results"][0]["status"] == "SINCRONIZADA"
    unauthorized = _op(cashier, inventory)
    unauthorized["operation_type"] = "pago.solicitar"
    rejected = client.post("/api/sync/batch", headers=device_headers,
                           json={"operations": [unauthorized]})
    assert rejected.status_code == 403


def test_offline_pos_rejects_another_tenant_scope(db):
    client, cashier, inventory, headers = _setup(db)
    outsider_scope_op = _op(cashier, inventory)
    outsider_scope_op["tenant_scope"] = "org:999"
    result = client.post("/api/sync/batch", headers=headers, json={"operations": [outsider_scope_op]})
    assert result.json()["results"][0]["status"] == "RECHAZADA"
    assert result.json()["results"][0]["category"] == "NO_AUTORIZADA"
    assert db.scalar(select(func.count()).select_from(Pedido)) == 0
