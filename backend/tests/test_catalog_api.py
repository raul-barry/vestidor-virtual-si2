from decimal import Decimal

from fastapi.testclient import TestClient

from app.main import app
from app.models.categoria import Categoria
from app.models.color import Color
from app.models.producto import Producto
from app.models.producto_variante import ProductoVariante
from app.models.talla import Talla


def test_get_catalog_products_is_public_and_returns_public_data(db) -> None:
    categoria = Categoria(nombre="Camisas", descripcion="Prendas superiores")
    producto = Producto(
        categoria=categoria,
        nombre="Camisa Oxford",
        descripcion="Camisa formal masculina",
        precio_base=Decimal("250.00"),
        estado="ACTIVO",
    )
    talla = Talla(nombre="M")
    color = Color(nombre="Blanco")
    variante = ProductoVariante(producto=producto, talla=talla, color=color, sku="CAM001-M-BLA")
    db.add_all([categoria, producto, talla, color, variante])
    db.commit()

    response = TestClient(app).get("/api/catalog/products")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id_producto": 1,
            "nombre": "Camisa Oxford",
            "descripcion": "Camisa formal masculina",
            "precio_base": "250.00",
            "estado": "ACTIVO",
            "categoria": {"id_categoria": 1, "nombre": "Camisas"},
            "variantes": [
                {"id_variante": 1, "sku": "CAM001-M-BLA", "talla": "M", "color": "Blanco"}
            ],
        }
    ]
    assert "password_hash" not in response.text
    assert "id_talla" not in response.text
    assert "id_color" not in response.text


def test_catalog_endpoint_is_documented_in_openapi() -> None:
    operation = app.openapi()["paths"]["/api/catalog/products"]["get"]

    assert "200" in operation["responses"]
    assert operation["responses"]["200"]["content"]["application/json"]["example"]
