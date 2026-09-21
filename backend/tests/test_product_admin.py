from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from conftest import session_token
from app.main import app
from app.models.categoria import Categoria
from app.models.producto import Producto
from app.models.rol import Rol
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
    token = session_token(db, {"id_usuario": user.id_usuario, "rol": role.nombre})
    return {"Authorization": f"Bearer {token}"}


def create_category(db) -> Categoria:
    category = Categoria(nombre="Camisas", descripcion=None)
    db.add(category)
    db.commit()
    return category


def test_admin_can_create_product_and_reject_duplicate(db) -> None:
    headers = create_headers(db, "ADMINISTRADOR", "admin@example.com")
    category = create_category(db)
    client = TestClient(app)
    payload = {
        "nombre": "Camisa Oxford",
        "descripcion": "Camisa formal",
        "precio_base": 250,
        "id_categoria": category.id_categoria,
    }

    created = client.post("/api/admin/products", headers=headers, json=payload)
    duplicate = client.post("/api/admin/products", headers=headers, json=payload)

    assert created.status_code == 201
    assert created.json()["estado"] == "ACTIVO"
    assert created.json()["categoria"]["nombre"] == "Camisas"
    assert duplicate.status_code == 409


def test_admin_can_list_products(db) -> None:
    headers = create_headers(db, "ADMINISTRADOR", "admin@example.com")
    category = create_category(db)
    db.add(Producto(id_categoria=category.id_categoria, nombre="Camisa Oxford", descripcion=None, precio_base=Decimal("250")))
    db.commit()

    response = TestClient(app).get("/api/admin/products", headers=headers)

    assert response.status_code == 200
    assert response.json()[0]["nombre"] == "Camisa Oxford"


def test_admin_can_update_and_disable_product(db) -> None:
    headers = create_headers(db, "ADMINISTRADOR", "admin@example.com")
    category = create_category(db)
    product = Producto(id_categoria=category.id_categoria, nombre="Camisa Oxford", descripcion=None, precio_base=Decimal("250"))
    db.add(product)
    db.commit()
    client = TestClient(app)

    updated = client.put(
        f"/api/admin/products/{product.id_producto}",
        headers=headers,
        json={"nombre": "Camisa Oxford Premium", "precio_base": 300},
    )
    disabled = client.delete(f"/api/admin/products/{product.id_producto}", headers=headers)

    assert updated.status_code == 200
    assert updated.json()["nombre"] == "Camisa Oxford Premium"
    assert disabled.status_code == 200
    assert disabled.json()["estado"] == "INACTIVO"


def test_admin_rejects_unknown_category_and_product(db) -> None:
    headers = create_headers(db, "ADMINISTRADOR", "admin@example.com")
    client = TestClient(app)

    category_response = client.post(
        "/api/admin/products",
        headers=headers,
        json={"nombre": "Camisa Oxford", "descripcion": None, "precio_base": 250, "id_categoria": 999},
    )
    product_response = client.put("/api/admin/products/999", headers=headers, json={"nombre": "Otro"})

    assert category_response.status_code == 404
    assert product_response.status_code == 404


def test_customer_cannot_access_administrative_products(db) -> None:
    headers = create_headers(db, "CLIENTE", "cliente@example.com")

    response = TestClient(app).get("/api/admin/products", headers=headers)

    assert response.status_code == 403


def test_admin_uploads_replaces_and_deletes_product_image_visible_in_catalog(db) -> None:
    headers = create_headers(db, "ADMINISTRADOR", "images-admin@example.com")
    category = create_category(db)
    product = Producto(
        id_categoria=category.id_categoria,
        nombre="Producto con imagen",
        descripcion="Imagen administrada",
        precio_base=Decimal("199.90"),
    )
    db.add(product)
    db.commit()
    client = TestClient(app)

    uploaded = client.post(
        f"/api/admin/products/{product.id_producto}/image",
        headers=headers,
        files={"file": ("producto.png", b"\x89PNG\r\n\x1a\ncontenido-prueba", "image/png")},
    )

    assert uploaded.status_code == 200
    image_url = uploaded.json()["imagen_url"]
    assert image_url.startswith("/api/assets/uploads/")
    assert client.get(image_url).status_code == 200

    admin_product = next(
        item for item in client.get("/api/admin/products", headers=headers).json()
        if item["id_producto"] == product.id_producto
    )
    catalog_product = next(
        item for item in client.get("/api/catalog/products").json()
        if item["id_producto"] == product.id_producto
    )
    assert admin_product["imagen_url"] == image_url
    assert catalog_product["imagen_url"] == image_url

    replacement = client.post(
        f"/api/admin/products/{product.id_producto}/image",
        headers=headers,
        files={"file": ("reemplazo.webp", b"RIFF\x04\x00\x00\x00WEBPcontenido", "image/webp")},
    )
    assert replacement.status_code == 200
    replacement_url = replacement.json()["imagen_url"]
    assert replacement_url != image_url
    assert client.get(image_url).status_code == 404
    assert client.get(replacement_url).status_code == 200

    deleted = client.delete(f"/api/admin/products/{product.id_producto}/image", headers=headers)
    assert deleted.status_code == 204
    assert client.get(replacement_url).status_code == 404
