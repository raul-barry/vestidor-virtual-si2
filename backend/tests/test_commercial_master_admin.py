from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from conftest import session_token
from app.main import app
from app.models.categoria import Categoria
from app.models.producto import Producto
from app.models.rol import Rol
from app.models.usuario import Usuario


def admin_headers(db) -> dict[str, str]:
    role = Rol(nombre="ADMINISTRADOR", descripcion="Administración")
    db.add(role)
    db.flush()
    user = Usuario(
        id_rol=role.id_rol,
        nombres="Admin",
        apellidos="Masters",
        correo="masters@example.com",
        password_hash="hash",
    )
    db.add(user)
    db.commit()
    token = session_token(db, {"id_usuario": user.id_usuario, "rol": role.nombre})
    return {"Authorization": f"Bearer {token}"}


def test_supplier_crud_with_logical_status(db) -> None:
    client = TestClient(app)
    headers = admin_headers(db)
    payload = {
        "nombre": "Textiles Andinos SRL",
        "descripcion": "Proveedor nacional",
        "persona_contacto": "Ana Pérez",
        "telefono": "70000000",
        "correo": "ana@textiles.test",
        "direccion": "Av. Principal 100",
        "estado": "ACTIVO",
    }

    created = client.post("/api/admin/suppliers", headers=headers, json=payload)
    assert created.status_code == 201, created.text
    supplier_id = created.json()["id_proveedor"]
    assert created.json()["persona_contacto"] == "Ana Pérez"

    updated = client.put(
        f"/api/admin/suppliers/{supplier_id}",
        headers=headers,
        json={**payload, "telefono": "71111111"},
    )
    disabled = client.patch(
        f"/api/admin/suppliers/{supplier_id}/status",
        headers=headers,
        json={"estado": "INACTIVO"},
    )
    restored = client.patch(
        f"/api/admin/suppliers/{supplier_id}/status",
        headers=headers,
        json={"estado": "ACTIVO"},
    )

    assert updated.status_code == 200 and updated.json()["telefono"] == "71111111"
    assert disabled.status_code == 200 and disabled.json()["estado"] == "INACTIVO"
    assert restored.status_code == 200 and restored.json()["estado"] == "ACTIVO"
    assert any(row["id_proveedor"] == supplier_id for row in client.get("/api/admin/suppliers", headers=headers).json())


def test_collection_crud_and_product_association(db) -> None:
    client = TestClient(app)
    headers = admin_headers(db)
    category = Categoria(nombre="Accesorios", descripcion="")
    db.add(category)
    db.flush()
    product = Producto(
        id_categoria=category.id_categoria,
        nombre="Bolso de temporada",
        descripcion="",
        precio_base=Decimal("299.00"),
    )
    db.add(product)
    db.commit()
    payload = {
        "nombre": "Primavera 2027",
        "descripcion": "Colección de primavera",
        "temporada": "PRIMAVERA",
        "anio": 2027,
        "fecha_inicio": "2027-09-01",
        "fecha_fin": "2027-11-30",
        "estado": "ACTIVO",
    }

    created = client.post("/api/admin/collections", headers=headers, json=payload)
    assert created.status_code == 201, created.text
    collection_id = created.json()["id_coleccion"]
    assert client.put(
        f"/api/admin/collections/{collection_id}",
        headers=headers,
        json={**payload, "descripcion": "Colección actualizada"},
    ).status_code == 200
    associated = client.put(
        f"/api/admin/collections/{collection_id}/products/{product.id_producto}",
        headers=headers,
    )
    assert associated.status_code == 200
    products = client.get(f"/api/admin/collections/{collection_id}/products", headers=headers)
    assert products.status_code == 200 and products.json()[0]["id_producto"] == product.id_producto
    removed = client.delete(
        f"/api/admin/collections/{collection_id}/products/{product.id_producto}",
        headers=headers,
    )
    assert removed.status_code == 204
    assert client.get(f"/api/admin/collections/{collection_id}/products", headers=headers).json() == []
    status_response = client.patch(
        f"/api/admin/collections/{collection_id}/status",
        headers=headers,
        json={"estado": "INACTIVO"},
    )
    assert status_response.status_code == 200 and status_response.json()["estado"] == "INACTIVO"
    assert db.scalar(select(Producto).where(Producto.id_producto == product.id_producto)).id_coleccion is None


def test_collection_rejects_inverted_dates(db) -> None:
    client = TestClient(app)
    headers = admin_headers(db)
    response = client.post(
        "/api/admin/collections",
        headers=headers,
        json={"nombre": "Fechas inválidas", "fecha_inicio": "2027-12-01", "fecha_fin": "2027-01-01"},
    )
    assert response.status_code == 422
