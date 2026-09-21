from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from conftest import session_token
from app.main import app
from app.models.categoria import Categoria
from app.models.color import Color
from app.models.producto import Producto
from app.models.rol import Rol
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
    token = session_token(db, {"id_usuario": user.id_usuario, "rol": role.nombre})
    return {"Authorization": f"Bearer {token}"}


def create_catalog_data(db) -> tuple[Producto, Talla, Talla, Color, Color]:
    category = Categoria(nombre="Camisas", descripcion=None)
    product = Producto(id_categoria=1, nombre="Camisa Oxford", descripcion=None, precio_base=Decimal("250"))
    size_m = Talla(nombre="M")
    size_l = Talla(nombre="L")
    color_white = Color(nombre="Blanco")
    color_blue = Color(nombre="Azul")
    db.add(category)
    db.flush()
    product.id_categoria = category.id_categoria
    db.add_all([product, size_m, size_l, color_white, color_blue])
    db.commit()
    return product, size_m, size_l, color_white, color_blue


def test_admin_can_create_and_list_variants(db) -> None:
    headers = create_headers(db, "ADMINISTRADOR", "admin@example.com")
    product, size_m, _, color_white, _ = create_catalog_data(db)
    client = TestClient(app)
    payload = {"sku": "OXF-M-BLA", "id_talla": size_m.id_talla, "id_color": color_white.id_color}

    created = client.post(f"/api/admin/products/{product.id_producto}/variants", headers=headers, json=payload)
    listed = client.get(f"/api/admin/products/{product.id_producto}/variants", headers=headers)

    assert created.status_code == 201
    assert created.json()["estado"] == "ACTIVO"
    assert created.json()["producto"] == "Camisa Oxford"
    assert listed.status_code == 200
    assert listed.json()[0]["sku"] == "OXF-M-BLA"


def test_admin_can_update_and_disable_variant(db) -> None:
    headers = create_headers(db, "ADMINISTRADOR", "admin@example.com")
    product, size_m, size_l, color_white, color_blue = create_catalog_data(db)
    client = TestClient(app)
    created = client.post(
        f"/api/admin/products/{product.id_producto}/variants",
        headers=headers,
        json={"sku": "OXF-M-BLA", "id_talla": size_m.id_talla, "id_color": color_white.id_color},
    )
    variant_id = created.json()["id_variante"]

    updated = client.put(
        f"/api/admin/variants/{variant_id}",
        headers=headers,
        json={"sku": "OXF-L-AZU", "id_talla": size_l.id_talla, "id_color": color_blue.id_color},
    )
    disabled = client.delete(f"/api/admin/variants/{variant_id}", headers=headers)

    assert updated.status_code == 200
    assert updated.json()["sku"] == "OXF-L-AZU"
    assert updated.json()["talla"] == "L"
    assert disabled.status_code == 200
    assert disabled.json()["estado"] == "INACTIVO"


def test_admin_rejects_duplicate_sku_and_invalid_references(db) -> None:
    headers = create_headers(db, "ADMINISTRADOR", "admin@example.com")
    product, size_m, _, color_white, _ = create_catalog_data(db)
    client = TestClient(app)
    payload = {"sku": "OXF-M-BLA", "id_talla": size_m.id_talla, "id_color": color_white.id_color}
    client.post(f"/api/admin/products/{product.id_producto}/variants", headers=headers, json=payload)

    duplicate = client.post(f"/api/admin/products/{product.id_producto}/variants", headers=headers, json=payload)
    product_missing = client.post("/api/admin/products/999/variants", headers=headers, json=payload)
    size_missing = client.post(
        f"/api/admin/products/{product.id_producto}/variants",
        headers=headers,
        json={"sku": "OXF-X-BLA", "id_talla": 999, "id_color": color_white.id_color},
    )
    color_missing = client.post(
        f"/api/admin/products/{product.id_producto}/variants",
        headers=headers,
        json={"sku": "OXF-M-X", "id_talla": size_m.id_talla, "id_color": 999},
    )

    assert duplicate.status_code == 409
    assert product_missing.status_code == 404
    assert size_missing.status_code == 404
    assert color_missing.status_code == 404


def test_customer_cannot_access_administrative_variants(db) -> None:
    headers = create_headers(db, "CLIENTE", "cliente@example.com")

    response = TestClient(app).get("/api/admin/products/1/variants", headers=headers)

    assert response.status_code == 403
