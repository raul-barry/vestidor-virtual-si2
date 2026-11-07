from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select

from app.models.audit_log import AuditLog
from app.models.cliente import Cliente
from app.models.inventario import Inventario
from app.models.pago import Pago
from app.models.pedido import Pedido
from app.models.reserva import Reserva
from app.models.usuario import Usuario
from app.services.reservation_expiration_service import ReservationExpirationService
from conftest import session_token
from test_sync_reservations import _operation
from app.main import app
from fastapi.testclient import TestClient
from app.database.seed import seed_initial_data


def _seeded_client(db):
    seed_initial_data(db)
    db.commit()
    user = db.scalar(select(Usuario).where(Usuario.correo == "cliente@vestidor.local"))
    token = session_token(db, {"id_usuario": user.id_usuario, "rol": "CLIENTE"})
    return TestClient(app), user, {"Authorization": f"Bearer {token}"}


def _create_reservation(client, user, headers, inventory):
    operation = _operation(user, "reserva.crear", {
        "id_inventario": inventory.id_inventario, "cantidad": 1,
    }, operation_uuid=uuid4())
    result = client.post("/api/sync/batch", headers=headers,
                         json={"operations": [operation]}).json()["results"][0]
    assert result["status"] == "SINCRONIZADA"
    return result["result"]["id_reserva"]


def test_expiration_releases_stock_and_writes_one_audit_event(db):
    client, user, headers = _seeded_client(db)
    inventory = db.scalar(select(Inventario).where(Inventario.stock_disponible > 0))
    original_available = inventory.stock_disponible
    reservation_id = _create_reservation(client, user, headers, inventory)
    reservation = db.get(Reserva, reservation_id)
    reservation.fecha_expiracion = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()

    service = ReservationExpirationService(db)
    first = service.process_expired()
    second = service.process_expired()

    assert first == {"expiradas": 1, "inconsistencias_inventario": 0}
    assert second == {"expiradas": 0, "inconsistencias_inventario": 0}
    db.refresh(inventory)
    db.refresh(reservation)
    assert reservation.estado == "EXPIRADA"
    assert (inventory.stock_disponible, inventory.stock_reservado) == (original_available, 0)
    assert db.scalar(select(AuditLog.id).where(
        AuditLog.dedupe_key == f"reservation-expiration:{reservation_id}"
    )) is not None


def test_expiration_skips_completed_and_paid_order_reservations(db):
    client, user, headers = _seeded_client(db)
    inventory = db.scalar(select(Inventario).where(Inventario.stock_disponible > 1))
    completed_id = _create_reservation(client, user, headers, inventory)
    paid_order_reservation_id = _create_reservation(client, user, headers, inventory)
    completed = db.get(Reserva, completed_id)
    paid_reservation = db.get(Reserva, paid_order_reservation_id)
    due = datetime.now(timezone.utc) - timedelta(seconds=1)
    completed.estado = "COMPLETADA"
    completed.fecha_expiracion = due

    customer = db.scalar(select(Cliente).where(Cliente.id_usuario == user.id_usuario))
    order = Pedido(id_cliente=customer.id_cliente, fecha_pedido=datetime.now(timezone.utc),
                   estado="PAGADO", total=Decimal("1.00"))
    db.add(order)
    db.flush([order])
    db.add(Pago(id_pedido=order.id_pedido, metodo_pago="PRUEBA", monto=Decimal("1.00"), estado="PAGADO"))
    paid_reservation.id_pedido = order.id_pedido
    paid_reservation.fecha_expiracion = due
    db.commit()
    before = (inventory.stock_disponible, inventory.stock_reservado)

    result = ReservationExpirationService(db).process_expired()

    assert result == {"expiradas": 0, "inconsistencias_inventario": 0}
    db.refresh(completed)
    db.refresh(paid_reservation)
    db.refresh(order)
    db.refresh(inventory)
    assert completed.estado == "COMPLETADA"
    assert paid_reservation.estado == "PENDIENTE"
    assert order.estado == "PAGADO"
    assert (inventory.stock_disponible, inventory.stock_reservado) == before


def test_expiration_uses_audit_and_inventory_scope_of_reservation_owner(db):
    client, user, headers = _seeded_client(db)
    inventory = db.scalar(select(Inventario).where(Inventario.stock_disponible > 0))
    reservation_id = _create_reservation(client, user, headers, inventory)
    reservation = db.get(Reserva, reservation_id)
    reservation.fecha_expiracion = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()

    ReservationExpirationService(db).process_expired()

    audit = db.scalar(select(AuditLog).where(
        AuditLog.dedupe_key == f"reservation-expiration:{reservation_id}"
    ))
    assert audit is not None
    assert audit.organizacion_id == user.id_organizacion
    assert audit.rol == "SISTEMA"
