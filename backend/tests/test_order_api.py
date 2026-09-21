from decimal import Decimal

from fastapi.testclient import TestClient

from app.database.seed import seed_roles
from app.main import app
from app.models.categoria import Categoria
from app.models.color import Color
from app.models.producto import Producto
from app.models.producto_variante import ProductoVariante
from app.models.talla import Talla
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
    branch = Sucursal(nombre="Sucursal de recojo", direccion="Av. Central 100", estado="ACTIVA")
    db.add(branch)
    db.commit()
    added = client.post("/api/cart/items", headers=headers, json={"id_variante": variant_id, "cantidad": 2})
    assert added.status_code == 200
    response = client.post(
        "/api/orders", headers=headers,
        json={"tipo_entrega": "RECOJO_SUCURSAL", "id_sucursal_entrega": branch.id_sucursal},
    )
    assert response.status_code == 201
    return response.json()["id_pedido"]


def test_create_order_from_active_cart(db) -> None:
    seed_roles(db)
    db.commit()
    client = TestClient(app)
    headers = register_and_login(client, "cliente@example.com")

    order_id = create_order_for_client(db, client, headers)

    response = client.get(f"/api/orders/{order_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["estado"] == "PENDIENTE"
    assert response.json()["total"] == "500.00"
    assert response.json()["tipo_entrega"] == "RECOJO_SUCURSAL"
    assert response.json()["id_sucursal_entrega"]
    assert response.json()["detalles"][0] == {
        "producto": "Camisa Oxford",
        "talla": "M",
        "color": "Blanco",
        "cantidad": 2,
        "precio_unitario": "250.00",
    }


def test_get_order_history_for_authenticated_client(db) -> None:
    seed_roles(db)
    db.commit()
    client = TestClient(app)
    headers = register_and_login(client, "cliente@example.com")
    order_id = create_order_for_client(db, client, headers)

    response = client.get("/api/orders", headers=headers)

    assert response.status_code == 200
    assert response.json()[0]["id_pedido"] == order_id
    assert "detalles" not in response.json()[0]


def test_create_order_rejects_empty_cart(db) -> None:
    seed_roles(db)
    db.commit()
    client = TestClient(app)
    headers = register_and_login(client, "cliente@example.com")
    client.get("/api/cart", headers=headers)

    response = client.post(
        "/api/orders", headers=headers,
        json={"tipo_entrega": "RECOJO_SUCURSAL", "id_sucursal_entrega": 1},
    )

    assert response.status_code == 400
    assert response.json()["message"] == "No se puede crear un pedido con un carrito vacío"


def test_legacy_order_request_without_delivery_details_remains_supported(db) -> None:
    seed_roles(db)
    db.commit()
    client = TestClient(app)
    headers = register_and_login(client, "legacy@example.com")
    variant_id = create_variant(db)
    assert client.post("/api/cart/items", headers=headers, json={"id_variante": variant_id, "cantidad": 1}).status_code == 200

    response = client.post("/api/orders", headers=headers, json={})

    assert response.status_code == 201
    assert client.get(f"/api/orders/{response.json()['id_pedido']}", headers=headers).json()["tipo_entrega"] is None


def test_client_cannot_access_another_clients_order(db) -> None:
    seed_roles(db)
    db.commit()
    client = TestClient(app)
    first_headers = register_and_login(client, "primero@example.com")
    order_id = create_order_for_client(db, client, first_headers)
    second_headers = register_and_login(client, "segundo@example.com")

    response = client.get(f"/api/orders/{order_id}", headers=second_headers)

    assert response.status_code == 404
    assert response.json()["message"] == "Pedido no encontrado"


def test_delivery_persists_address_and_active_branch_lookup(db) -> None:
    seed_roles(db)
    db.commit()
    client = TestClient(app)
    headers = register_and_login(client, "delivery@example.com")
    variant_id = create_variant(db)
    active = Sucursal(nombre="Activa", direccion="Centro", estado="ACTIVA")
    inactive = Sucursal(nombre="Inactiva", direccion="Norte", estado="INACTIVA")
    db.add_all([active, inactive])
    db.commit()
    assert client.post("/api/cart/items", headers=headers, json={"id_variante": variant_id, "cantidad": 1}).status_code == 200

    branches = client.get("/api/orders/delivery-branches", headers=headers)
    response = client.post(
        "/api/orders", headers=headers,
        json={
            "tipo_entrega": "DELIVERY", "direccion_entrega": "Av. Siempre Viva 123",
            "referencia_entrega": "Portón azul", "telefono_entrega": "70000000",
        },
    )

    assert branches.status_code == 200
    assert [branch["id_sucursal"] for branch in branches.json()] == [active.id_sucursal]
    assert response.status_code == 201
    detail = client.get(f"/api/orders/{response.json()['id_pedido']}", headers=headers).json()
    assert detail["direccion_entrega"] == "Av. Siempre Viva 123"
    assert detail["referencia_entrega"] == "Portón azul"
    assert detail["telefono_entrega"] == "70000000"
