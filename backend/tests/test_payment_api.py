from decimal import Decimal

from fastapi.testclient import TestClient

from app.database.seed import seed_roles
from app.main import app
from app.models.categoria import Categoria
from app.models.color import Color
from app.models.producto import Producto
from app.models.producto_variante import ProductoVariante
from app.models.talla import Talla
from app.models.inventario import Inventario
from app.models.sucursal import Sucursal


def create_variant(db) -> int:
    categoria = Categoria(nombre="Camisas", descripcion=None)
    producto = Producto(
        categoria=categoria,
        nombre="Camisa Oxford",
        descripcion=None,
        precio_base=Decimal("250.00"),
    )
    talla = Talla(nombre="M")
    color = Color(nombre="Blanco")
    variante = ProductoVariante(producto=producto, talla=talla, color=color, sku="OXF-M-BLA")
    db.add_all([categoria, producto, talla, color, variante])
    db.add(Inventario(variante=variante, sucursal=Sucursal(nombre="Central", direccion="Centro"), stock_disponible=10))
    db.commit()
    return variante.id_variante


def register_and_login(client: TestClient, correo: str) -> dict[str, str]:
    registration = client.post(
        "/api/auth/register",
        json={
            "nombres": "Carlos",
            "apellidos": "Perez",
            "correo": correo,
            "telefono": "70000000",
            "password": "password-seguro",
        },
    )
    assert registration.status_code == 201
    login = client.post("/api/auth/login", json={"correo": correo, "password": "password-seguro"})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def create_order_for_client(db, client: TestClient, headers: dict[str, str]) -> int:
    variant_id = create_variant(db)
    added = client.post("/api/cart/items", headers=headers, json={"id_variante": variant_id, "cantidad": 2})
    assert added.status_code == 200
    order = client.post("/api/orders", headers=headers)
    assert order.status_code == 201
    return order.json()["id_pedido"]


def test_create_and_get_payment_for_own_order(db) -> None:
    seed_roles(db)
    db.commit()
    client = TestClient(app)
    headers = register_and_login(client, "cliente@example.com")
    order_id = create_order_for_client(db, client, headers)

    created = client.post("/api/payments", headers=headers, json={"id_pedido": order_id, "metodo_pago": "QR"})
    fetched = client.get(f"/api/payments/order/{order_id}", headers=headers)

    assert created.status_code == 200
    assert created.json()["estado"] == "PENDIENTE"
    assert created.json()["monto"] == "500.00"
    assert fetched.status_code == 200
    assert fetched.json()["id_pago"] == created.json()["id_pago"]


def test_approve_payment_confirms_order(db) -> None:
    seed_roles(db)
    db.commit()
    client = TestClient(app)
    headers = register_and_login(client, "cliente@example.com")
    order_id = create_order_for_client(db, client, headers)
    payment = client.post(
        "/api/payments", headers=headers, json={"id_pedido": order_id, "metodo_pago": "TARJETA"}
    )

    response = client.put(f"/api/payments/{payment.json()['id_pago']}/approve", headers=headers)
    order = client.get(f"/api/orders/{order_id}", headers=headers)

    assert response.status_code == 200
    assert response.json()["estado"] == "APROBADO"
    assert order.json()["estado"] == "CONFIRMADO"


def test_reject_payment(db) -> None:
    seed_roles(db)
    db.commit()
    client = TestClient(app)
    headers = register_and_login(client, "cliente@example.com")
    order_id = create_order_for_client(db, client, headers)
    payment = client.post(
        "/api/payments", headers=headers, json={"id_pedido": order_id, "metodo_pago": "EFECTIVO"}
    )

    response = client.put(f"/api/payments/{payment.json()['id_pago']}/reject", headers=headers)

    assert response.status_code == 200
    assert response.json()["estado"] == "RECHAZADO"


def test_duplicate_payment_is_rejected(db) -> None:
    seed_roles(db)
    db.commit()
    client = TestClient(app)
    headers = register_and_login(client, "cliente@example.com")
    order_id = create_order_for_client(db, client, headers)
    payload = {"id_pedido": order_id, "metodo_pago": "QR"}
    client.post("/api/payments", headers=headers, json=payload)

    response = client.post("/api/payments", headers=headers, json=payload)

    assert response.status_code == 409
    assert response.json()["message"] == "El pedido ya tiene un pago creado"


def test_client_cannot_operate_another_clients_payment(db) -> None:
    seed_roles(db)
    db.commit()
    client = TestClient(app)
    first_headers = register_and_login(client, "primero@example.com")
    order_id = create_order_for_client(db, client, first_headers)
    payment = client.post(
        "/api/payments", headers=first_headers, json={"id_pedido": order_id, "metodo_pago": "QR"}
    )
    second_headers = register_and_login(client, "segundo@example.com")

    create_response = client.post(
        "/api/payments", headers=second_headers, json={"id_pedido": order_id, "metodo_pago": "QR"}
    )
    approve_response = client.put(
        f"/api/payments/{payment.json()['id_pago']}/approve", headers=second_headers
    )

    assert create_response.status_code == 404
    assert approve_response.status_code == 404
