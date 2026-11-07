from sqlalchemy import func, select

from app.models.audit_log import AuditLog
from app.models.inventario import Inventario
from app.models.pago import Pago
from app.models.pedido import Pedido
from app.models.pedido_detalle import PedidoDetalle
from app.models.reserva import Reserva
from app.services.payment_service import PaymentService
from app.models.usuario import Usuario
from conftest import session_token
from fastapi.testclient import TestClient
from app.main import app
from app.database.seed import seed_initial_data
from test_sync_reservations import _operation


def _sale_client(db):
    seed_initial_data(db)
    db.commit()
    user = db.scalar(select(Usuario).where(Usuario.correo == "cliente@vestidor.local"))
    token = session_token(db, {"id_usuario": user.id_usuario, "rol": "CLIENTE"})
    return TestClient(app), user, {"Authorization": f"Bearer {token}"}


def _sale_operation(user, inventory, lines, *, client_id="sale-device", operation_uuid=None):
    return _operation(user, "venta.crear", {
        "lineas": lines,
        "metodo_pago": "EFECTIVO",
        "entrega": {"tipo_entrega": "RECOJO_SUCURSAL", "id_sucursal_entrega": inventory.id_sucursal},
        # Ordinary sale tests must not imply that cash was actually collected.
        "datos_pago": {},
    }, client_id=client_id, operation_uuid=operation_uuid)


def test_offline_sale_recalculates_server_price_holds_stock_and_replays_idempotently(db):
    client, user, headers = _sale_client(db)
    inventory = db.scalar(select(Inventario).where(Inventario.stock_disponible > 0))
    original = inventory.stock_disponible
    operation = _sale_operation(user, inventory, [
        {"client_line_id": "line-1", "id_variante": inventory.id_variante, "cantidad": 1,
            "precio_unitario": "0.01", "total": "0.01"},
    ])

    first = client.post("/api/sync/batch", headers=headers, json={"operations": [operation]})
    replay = client.post("/api/sync/batch", headers=headers, json={"operations": [operation]})

    result = first.json()["results"][0]
    assert first.status_code == replay.status_code == 200
    assert result["status"] == "SINCRONIZADA"
    assert result["result"]["pedido"]["total"] != "0.01"
    assert result["result"]["pedido"]["estado_pago"] == "PENDIENTE"
    assert replay.json()["results"][0]["duplicate"] is True
    assert db.scalar(select(func.count()).select_from(Pedido)) == 1
    assert db.scalar(select(func.count()).select_from(Pago)) == 1
    assert db.scalar(select(func.count()).select_from(PedidoDetalle)) == 1
    db.refresh(inventory)
    assert (inventory.stock_disponible, inventory.stock_reservado, inventory.stock_vendido) == (original - 1, 1, 0)
    reservation = db.scalar(select(Reserva).where(Reserva.id_pedido == result["result"]["pedido"]["id_pedido"]))
    assert reservation is not None and reservation.estado == "CONFIRMADA"
    assert db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.accion == "VENTA_OFFLINE_REGISTRADA")) == 1

    # The existing payment path consumes the hold once when authorization arrives.
    payment = db.scalar(select(Pago).where(Pago.id_pedido == reservation.id_pedido))
    PaymentService(db).approve_payment(payment.id_pago, user.cliente.id_cliente)
    db.refresh(inventory)
    db.refresh(payment)
    assert (inventory.stock_disponible, inventory.stock_reservado, inventory.stock_vendido) == (original - 1, 0, 1)
    assert payment.estado == "PAGADO"


def test_offline_sale_accepts_available_lines_and_returns_rejected_line_details(db):
    client, user, headers = _sale_client(db)
    inventories = db.scalars(select(Inventario).order_by(Inventario.id_inventario)).all()
    available, empty = inventories[:2]
    available.stock_disponible = 2
    empty.stock_disponible = 0
    db.commit()
    operation = _sale_operation(user, available, [
        {"client_line_id": "available", "id_variante": available.id_variante, "cantidad": 1},
        {"client_line_id": "empty", "id_variante": empty.id_variante, "cantidad": 1},
    ])

    response = client.post("/api/sync/batch", headers=headers, json={"operations": [operation]})

    result = response.json()["results"][0]
    assert response.status_code == 200
    assert result["status"] == "SINCRONIZADA"
    assert result["result"]["parcial"] is True
    assert [line["client_line_id"] for line in result["result"]["lineas_aceptadas"]] == ["available"]
    assert result["result"]["lineas_rechazadas"] == [{
        "client_line_id": "empty", "id_variante": empty.id_variante,
        "cantidad": 1, "motivo": "CONFLICTO_INVENTARIO",
    }]
    assert db.scalar(select(func.count()).select_from(Pedido)) == 1
    db.refresh(available)
    db.refresh(empty)
    assert (available.stock_disponible, available.stock_reservado) == (1, 1)
    assert (empty.stock_disponible, empty.stock_reservado) == (0, 0)


def test_offline_sale_with_all_lines_unavailable_creates_no_order(db):
    client, user, headers = _sale_client(db)
    inventory = db.scalar(select(Inventario).where(Inventario.stock_disponible > 0))
    inventory.stock_disponible = 0
    db.commit()
    operation = _sale_operation(user, inventory, [
        {"client_line_id": "empty", "id_variante": inventory.id_variante, "cantidad": 1},
    ])

    response = client.post("/api/sync/batch", headers=headers, json={"operations": [operation]})

    result = response.json()["results"][0]
    assert response.status_code == 200
    assert result["status"] == "RECHAZADA"
    assert result["category"] == "CONFLICTO_INVENTARIO"
    assert result["result"]["pedido"] is None
    assert result["result"]["lineas_rechazadas"][0]["client_line_id"] == "empty"
    assert db.scalar(select(func.count()).select_from(Pedido)) == 0
    assert db.scalar(select(func.count()).select_from(Pago)) == 0


def test_duplicate_variant_lines_cannot_overallocate_the_last_unit(db):
    client, user, headers = _sale_client(db)
    inventory = db.scalar(select(Inventario).where(Inventario.stock_disponible > 0))
    inventory.stock_disponible = 1
    db.commit()
    operation = _sale_operation(user, inventory, [
        {"client_line_id": "line-a", "id_variante": inventory.id_variante, "cantidad": 1},
        {"client_line_id": "line-b", "id_variante": inventory.id_variante, "cantidad": 1},
    ])

    result = client.post("/api/sync/batch", headers=headers, json={"operations": [operation]}).json()["results"][0]

    assert result["status"] == "SINCRONIZADA"
    assert [line["client_line_id"] for line in result["result"]["lineas_aceptadas"]] == ["line-a"]
    assert [line["client_line_id"] for line in result["result"]["lineas_rechazadas"]] == ["line-b"]
    db.refresh(inventory)
    assert (inventory.stock_disponible, inventory.stock_reservado) == (0, 1)


def test_limited_device_credential_can_sync_sale_but_not_other_operations(db):
    client, user, headers = _sale_client(db)
    inventory = db.scalar(select(Inventario).where(Inventario.stock_disponible > 0))
    credential = client.post("/api/sync/device-credentials", headers=headers, json={"client_id": "sale-device"})
    limited = {"Authorization": f"Bearer {credential.json()['sync_token']}"}

    sale = client.post("/api/sync/batch", headers=limited, json={"operations": [
        _sale_operation(user, inventory, [{"client_line_id": "x", "id_variante": inventory.id_variante, "cantidad": 1}])
    ]})
    other = client.post("/api/sync/batch", headers=limited, json={"operations": [
        _operation(user, "pedido.crear", {}, client_id="sale-device")
    ]})

    assert sale.status_code == 200
    assert sale.json()["results"][0]["status"] == "SINCRONIZADA"
    assert other.status_code == 403


def test_offline_cash_is_reconciled_against_server_total_and_records_change(db):
    client, user, headers = _sale_client(db)
    inventory = db.scalar(select(Inventario).where(Inventario.stock_disponible > 0))
    operation = _sale_operation(user, inventory, [
        {"client_line_id": "cash-line", "id_variante": inventory.id_variante, "cantidad": 1},
    ])
    operation["payload"]["datos_pago"]["importe_recibido"] = "999999.00"

    response = client.post("/api/sync/batch", headers=headers, json={"operations": [operation]})

    result = response.json()["results"][0]["result"]["pedido"]
    payment = db.scalar(select(Pago).where(Pago.id_pedido == result["id_pedido"]))
    assert response.status_code == 200
    assert result["estado_pago"] == "PAGADO"
    assert payment.cash_received == 999999
    assert payment.cash_change == 999999 - payment.monto
