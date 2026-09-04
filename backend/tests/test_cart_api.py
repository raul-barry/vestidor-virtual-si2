from decimal import Decimal

from fastapi.testclient import TestClient

from app.database.seed import seed_roles
from app.main import app
from app.models.categoria import Categoria
from app.models.color import Color
from app.models.producto import Producto
from app.models.producto_variante import ProductoVariante
from app.models.talla import Talla


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


def test_get_cart_creates_empty_cart_for_authenticated_client(db) -> None:
    seed_roles(db)
    db.commit()
    client = TestClient(app)
    headers = register_and_login(client, "cliente@example.com")

    response = client.get("/api/cart", headers=headers)

    assert response.status_code == 200
    assert response.json()["estado"] == "ACTIVO"
    assert response.json()["items"] == []
    assert response.json()["total"] == "0"


def test_add_item_creates_cart_and_detail(db) -> None:
    seed_roles(db)
    db.commit()
    variant_id = create_variant(db)
    client = TestClient(app)
    headers = register_and_login(client, "cliente@example.com")

    response = client.post("/api/cart/items", headers=headers, json={"id_variante": variant_id, "cantidad": 2})

    assert response.status_code == 200
    assert response.json()["items"][0]["cantidad"] == 2
    assert response.json()["total"] == "500.00"


def test_add_same_item_increases_quantity(db) -> None:
    seed_roles(db)
    db.commit()
    variant_id = create_variant(db)
    client = TestClient(app)
    headers = register_and_login(client, "cliente@example.com")

    client.post("/api/cart/items", headers=headers, json={"id_variante": variant_id, "cantidad": 1})
    response = client.post("/api/cart/items", headers=headers, json={"id_variante": variant_id, "cantidad": 2})

    assert response.status_code == 200
    assert len(response.json()["items"]) == 1
    assert response.json()["items"][0]["cantidad"] == 3


def test_update_and_delete_cart_item(db) -> None:
    seed_roles(db)
    db.commit()
    variant_id = create_variant(db)
    client = TestClient(app)
    headers = register_and_login(client, "cliente@example.com")
    added = client.post("/api/cart/items", headers=headers, json={"id_variante": variant_id, "cantidad": 1})
    item_id = added.json()["items"][0]["id_detalle"]

    updated = client.put(f"/api/cart/items/{item_id}", headers=headers, json={"cantidad": 5})
    deleted = client.delete(f"/api/cart/items/{item_id}", headers=headers)

    assert updated.status_code == 200
    assert updated.json()["items"][0]["cantidad"] == 5
    assert deleted.status_code == 200
    assert deleted.json()["items"] == []


def test_cart_requires_jwt(db) -> None:
    response = TestClient(app).get("/api/cart")

    assert response.status_code == 401


def test_clients_are_isolated_from_each_others_cart(db) -> None:
    seed_roles(db)
    db.commit()
    variant_id = create_variant(db)
    client = TestClient(app)
    first_headers = register_and_login(client, "primero@example.com")
    second_headers = register_and_login(client, "segundo@example.com")

    client.post("/api/cart/items", headers=first_headers, json={"id_variante": variant_id, "cantidad": 1})
    response = client.get("/api/cart", headers=second_headers)

    assert response.status_code == 200
    assert response.json()["items"] == []
