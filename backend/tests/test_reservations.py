from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.database.seed import seed_initial_data
from app.main import app
from app.models.inventario import Inventario
from app.models.movimiento_inventario import MovimientoInventario


def login(client, role):
    passwords = {"cliente": "Cliente123!", "encargado": "Encargado123!", "cajero": "Cajero123!"}
    response = client.post("/api/auth/login", json={"correo": f"{role}@vestidor.local", "password": passwords[role]})
    assert response.status_code == 200
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def test_reservation_full_flow_and_permissions(db):
    seed_initial_data(db)
    db.commit()
    client = TestClient(app)
    customer = login(client, "cliente")
    staff = login(client, "encargado")
    cashier = login(client, "cajero")
    inv = db.scalar(select(Inventario))
    original = inv.stock_disponible
    payload = {"id_inventario": inv.id_inventario, "cantidad": 2}
    assert client.post("/api/reservations", headers=cashier, json=payload).status_code == 403
    created = client.post("/api/reservations", headers=customer, json=payload)
    assert created.status_code == 201
    db.refresh(inv)
    assert (inv.stock_disponible, inv.stock_reservado) == (original - 2, 2)
    path = f"/api/reservations/{created.json()['id_reserva']}"
    assert client.put(path, headers=customer, json={"estado": "CONFIRMADA"}).status_code == 403
    assert client.put(path, headers=staff, json={"estado": "CONFIRMADA"}).status_code == 200
    assert client.put(path, headers=customer, json={"estado": "CANCELADA"}).status_code == 200
    repeated = client.put(path, headers=customer, json={"estado": "CANCELADA"})
    assert repeated.status_code == 200
    assert repeated.json()["estado"] == "CANCELADA"
    db.refresh(inv)
    assert inv.stock_disponible == original
    assert inv.stock_reservado == 0
    assert db.scalar(select(func.count()).select_from(MovimientoInventario).where(
        MovimientoInventario.tipo_movimiento == "LIBERACION_RESERVA"
    )) == 1
    db.refresh(inv)
    assert (inv.stock_disponible, inv.stock_reservado) == (original, 0)
    assert client.post("/api/reservations", headers=customer, json={**payload, "cantidad": original + 1}).status_code == 409


def test_payment_consumes_stock_once_and_rejects_shortage(db):
    seed_initial_data(db)
    db.commit()
    client = TestClient(app)
    customer = login(client, "cliente")
    inv = db.scalar(select(Inventario))
    original = inv.stock_disponible
    assert client.post('/api/cart/items', headers=customer, json={"id_variante": inv.id_variante, "cantidad": 2}).status_code == 200
    order = client.post('/api/orders', headers=customer).json()
    payment = client.post('/api/payments/qr', headers=customer, json={"id_pedido": order['id_pedido'], "metodo_pago": "QR"}).json()['payment']
    path = f"/api/payments/{payment['id_pago']}/approve"
    assert client.put(path, headers=customer).status_code == 200
    assert client.put(path, headers=customer).status_code == 409
    db.refresh(inv)
    assert inv.stock_disponible == original - 2
    assert client.post('/api/cart/items', headers=customer, json={"id_variante": inv.id_variante, "cantidad": 2}).status_code == 200
    order = client.post('/api/orders', headers=customer).json()
    payment = client.post('/api/payments', headers=customer, json={"id_pedido": order['id_pedido'], "metodo_pago": "QR"}).json()
    inv.stock_disponible = 0
    db.commit()
    assert client.put(f"/api/payments/{payment['id_pago']}/approve", headers=customer).status_code == 409
    fetched = client.get(f"/api/payments/order/{order['id_pedido']}", headers=customer)
    assert fetched.json()['estado'] == 'PENDIENTE'


def test_availability_can_be_filtered_by_selected_variant(db):
    seed_initial_data(db)
    db.commit()
    client = TestClient(app)
    customer = login(client, "cliente")
    inventory = db.scalar(select(Inventario))

    response = client.get(f"/api/reservations/availability?id_variante={inventory.id_variante}", headers=customer)

    assert response.status_code == 200
    assert response.json()
    assert all(row["id_variante"] == inventory.id_variante for row in response.json())
    assert all(row["disponible"] > 0 for row in response.json())
