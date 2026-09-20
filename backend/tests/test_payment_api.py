from decimal import Decimal
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.database.seed import seed_roles
from app.main import app
from app.core.config import settings
from app.models.categoria import Categoria
from app.models.color import Color
from app.models.producto import Producto
from app.models.producto_variante import ProductoVariante
from app.models.talla import Talla
from app.models.inventario import Inventario
from app.models.sucursal import Sucursal
from sqlalchemy import select


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
    branch = db.scalar(select(Sucursal).where(Sucursal.estado == "ACTIVA"))
    order = client.post(
        "/api/orders", headers=headers,
        json={"tipo_entrega": "RECOJO_SUCURSAL", "id_sucursal_entrega": branch.id_sucursal},
    )
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
    assert response.json()["estado"] == "PAGADO"
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
    assert response.json()["estado"] == "FALLIDO"


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


def test_stripe_webhook_accepts_a_successful_retry_after_failure(db, monkeypatch) -> None:
    from app.services.payment_service import PaymentService
    import stripe

    seed_roles(db)
    db.commit()
    client = TestClient(app)
    headers = register_and_login(client, "webhook@example.com")
    order = create_order_for_client(db, client, headers)
    service = PaymentService(db)
    payment_response = service.create_stripe_payment(
        order, None, {"id": "pi_retry", "client_secret": "secret", "status": "requires_payment_method"}
    )
    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec_test")
    events = {
        "failed": {"id": "evt_failed", "type": "payment_intent.payment_failed", "data": {"object": {"id": "pi_retry"}}},
        "succeeded": {"id": "evt_succeeded", "type": "payment_intent.succeeded", "data": {"object": {"id": "pi_retry"}}},
    }
    monkeypatch.setattr(stripe.Webhook, "construct_event", lambda _payload, signature, _secret: events[signature])
    failed = client.post("/api/payments/stripe/webhook", content=b"{}", headers={"stripe-signature": "failed"})
    payment = service.repository.get_payment_by_id(payment_response.id_pago)
    db.refresh(payment)
    assert failed.status_code == 200
    assert payment.estado == "FALLIDO"

    succeeded = client.post("/api/payments/stripe/webhook", content=b"{}", headers={"stripe-signature": "succeeded"})
    db.refresh(payment)
    assert succeeded.status_code == 200
    assert payment.estado == "PAGADO"
    inventory = db.scalar(select(Inventario))
    assert inventory.stock_disponible == 8
    duplicate = client.post("/api/payments/stripe/webhook", content=b"{}", headers={"stripe-signature": "succeeded"})
    db.refresh(inventory)
    assert duplicate.json() == {"status": "already_processed"}
    assert inventory.stock_disponible == 8


def test_stripe_create_intent_uses_order_total_without_real_charge(db, monkeypatch) -> None:
    import stripe

    seed_roles(db)
    db.commit()
    client = TestClient(app)
    headers = register_and_login(client, "intent@example.com")
    order_id = create_order_for_client(db, client, headers)
    captured: dict[str, object] = {}

    def create_intent(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(id="pi_mock", client_secret="secret_mock", status="requires_payment_method")

    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_mock")
    monkeypatch.setattr(settings, "stripe_publishable_key", "pk_test_mock")
    monkeypatch.setattr(settings, "stripe_currency", "BOB")
    monkeypatch.setattr(stripe.PaymentIntent, "create", create_intent)

    response = client.post("/api/payments/stripe/create-intent", headers=headers, json={"id_pedido": order_id})

    assert response.status_code == 200
    assert response.json()["client_secret"] == "secret_mock"
    assert captured["amount"] == 50000
    assert captured["currency"] == "bob"
    assert captured["idempotency_key"] == f"pedido-{order_id}"


def test_stripe_create_intent_is_controlled_when_keys_are_missing(db, monkeypatch) -> None:
    seed_roles(db)
    db.commit()
    client = TestClient(app)
    headers = register_and_login(client, "stripe-missing@example.com")
    order_id = create_order_for_client(db, client, headers)
    monkeypatch.setattr(settings, "stripe_secret_key", "")
    monkeypatch.setattr(settings, "stripe_publishable_key", "")

    response = client.post("/api/payments/stripe/create-intent", headers=headers, json={"id_pedido": order_id})

    assert response.status_code == 503
    assert response.json()["detail"] == "Stripe no est\u00e1 configurado actualmente."


def test_stripe_webhook_rejects_invalid_signature(db, monkeypatch) -> None:
    seed_roles(db)
    db.commit()
    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec_test")

    response = TestClient(app).post(
        "/api/payments/stripe/webhook", content=b"{}", headers={"stripe-signature": "invalid"}
    )

    assert response.status_code == 400


def test_authenticated_customer_smoke_routes_do_not_return_401(db) -> None:
    seed_roles(db)
    db.commit()
    client = TestClient(app)
    headers = register_and_login(client, "smoke@example.com")
    variant_id = create_variant(db)

    assert client.get("/api/cart", headers=headers).status_code == 200
    assert client.get("/api/orders", headers=headers).status_code == 200
    assert client.get("/api/users/profile", headers=headers).status_code == 200
    assert client.put("/api/body-profile", headers=headers, json={"consentimiento": True, "altura_cm": 170}).status_code == 200
    assert client.get("/api/body-profile", headers=headers).status_code == 200
    assert client.post("/api/cart/items", headers=headers, json={"id_variante": variant_id, "cantidad": 1}).status_code == 200
