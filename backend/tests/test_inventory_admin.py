from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.security import create_access_token
from app.main import app
from app.models.categoria import Categoria
from app.models.color import Color
from app.models.producto import Producto
from app.models.producto_variante import ProductoVariante
from app.models.rol import Rol
from app.models.sucursal import Sucursal
from app.models.talla import Talla
from app.models.usuario import Usuario


def create_headers(db, role_name: str, correo: str) -> dict[str, str]:
    role = db.scalar(select(Rol).where(Rol.nombre == role_name))
    if role is None:
        role = Rol(nombre=role_name, descripcion=None)
        db.add(role)
        db.flush()
    user = Usuario(
        id_rol=role.id_rol,
        nombres="Admin",
        apellidos="User",
        correo=correo,
        telefono=None,
        password_hash="hash",
    )
    db.add(user)
    db.commit()
    token = create_access_token({"id_usuario": user.id_usuario, "rol": role.nombre})
    return {"Authorization": f"Bearer {token}"}


def create_variant_and_branch(db) -> tuple[int, int]:
    category = Categoria(nombre="Camisas", descripcion=None)
    product = Producto(categoria=category, nombre="Camisa Oxford", descripcion=None, precio_base=Decimal("250"))
    size = Talla(nombre="M")
    color = Color(nombre="Blanco")
    variant = ProductoVariante(producto=product, talla=size, color=color, sku="OXF-M-BLA")
    branch = Sucursal(nombre="Sucursal Central", direccion="Av. Principal 100")
    db.add_all([category, product, size, color, variant, branch])
    db.commit()
    return variant.id_variante, branch.id_sucursal


def create_inventory(client: TestClient, headers: dict[str, str], variant_id: int, branch_id: int, stock: int = 50) -> int:
    response = client.post(
        "/api/admin/inventory",
        headers=headers,
        json={"id_variante": variant_id, "id_sucursal": branch_id, "stock": stock},
    )
    assert response.status_code == 201
    return response.json()["id_inventario"]


def test_create_and_list_inventory(db) -> None:
    headers = create_headers(db, "ADMINISTRADOR", "admin@example.com")
    variant_id, branch_id = create_variant_and_branch(db)
    client = TestClient(app)

    inventory_id = create_inventory(client, headers, variant_id, branch_id, stock=3)
    listed = client.get("/api/admin/inventory", headers=headers)

    assert inventory_id == 1
    assert listed.status_code == 200
    assert listed.json()[0]["stock"] == 3
    assert listed.json()[0]["stock_bajo"] is True


def test_increase_and_decrease_stock(db) -> None:
    headers = create_headers(db, "ADMINISTRADOR", "admin@example.com")
    variant_id, branch_id = create_variant_and_branch(db)
    client = TestClient(app)
    inventory_id = create_inventory(client, headers, variant_id, branch_id)

    increased = client.post(
        f"/api/admin/inventory/{inventory_id}/increase",
        headers=headers,
        json={"cantidad": 20, "motivo": "Nueva compra"},
    )
    decreased = client.post(
        f"/api/admin/inventory/{inventory_id}/decrease",
        headers=headers,
        json={"cantidad": 5, "motivo": "Producto vendido"},
    )

    assert increased.status_code == 200
    assert increased.json()["stock"] == 70
    assert decreased.status_code == 200
    assert decreased.json()["stock"] == 65


def test_prevents_negative_stock_and_allows_adjustment(db) -> None:
    headers = create_headers(db, "ADMINISTRADOR", "admin@example.com")
    variant_id, branch_id = create_variant_and_branch(db)
    client = TestClient(app)
    inventory_id = create_inventory(client, headers, variant_id, branch_id, stock=10)

    negative = client.post(
        f"/api/admin/inventory/{inventory_id}/decrease",
        headers=headers,
        json={"cantidad": 11, "motivo": "Salida excesiva"},
    )
    adjusted = client.put(
        f"/api/admin/inventory/{inventory_id}/adjust",
        headers=headers,
        json={"nuevo_stock": 30, "motivo": "Conteo físico"},
    )

    assert negative.status_code == 422
    assert adjusted.status_code == 200
    assert adjusted.json()["stock"] == 30


def test_history_and_duplicate_branch_variant_restriction(db) -> None:
    headers = create_headers(db, "ADMINISTRADOR", "admin@example.com")
    variant_id, branch_id = create_variant_and_branch(db)
    client = TestClient(app)
    inventory_id = create_inventory(client, headers, variant_id, branch_id)
    client.post(
        f"/api/admin/inventory/{inventory_id}/increase",
        headers=headers,
        json={"cantidad": 5, "motivo": "Nueva compra"},
    )
    duplicate = client.post(
        "/api/admin/inventory",
        headers=headers,
        json={"id_variante": variant_id, "id_sucursal": branch_id, "stock": 10},
    )
    history = client.get(f"/api/admin/inventory/{inventory_id}/movements", headers=headers)

    assert duplicate.status_code == 409
    assert history.status_code == 200
    assert [movement["tipo"] for movement in history.json()] == ["ENTRADA", "AJUSTE"]
    assert history.json()[0]["usuario"] == "Admin User"


def test_customer_cannot_access_inventory_administration(db) -> None:
    headers = create_headers(db, "CLIENTE", "cliente@example.com")

    response = TestClient(app).get("/api/admin/inventory", headers=headers)

    assert response.status_code == 403
