from decimal import Decimal

from fastapi.testclient import TestClient

from app.main import app
from app.models.categoria import Categoria
from app.models.color import Color
from app.models.producto import Producto
from app.models.producto_variante import ProductoVariante
from app.models.talla import Talla


def create_product_with_variants(db) -> int:
    categoria = Categoria(nombre="Camisas", descripcion=None)
    producto = Producto(categoria=categoria, nombre="Camisa Oxford", descripcion=None, precio_base=Decimal("250"))
    talla_m = Talla(nombre="M")
    talla_l = Talla(nombre="L")
    blanco = Color(nombre="Blanco")
    azul = Color(nombre="Azul")
    db.add_all(
        [
            categoria,
            producto,
            talla_m,
            talla_l,
            blanco,
            azul,
            ProductoVariante(producto=producto, talla=talla_m, color=blanco, sku="OXF-M-BLA"),
            ProductoVariante(producto=producto, talla=talla_l, color=azul, sku="OXF-L-AZU"),
        ]
    )
    db.commit()
    return producto.id_producto


def test_get_product_variants_returns_sizes_colors_and_variants(db) -> None:
    product_id = create_product_with_variants(db)

    response = TestClient(app).get(f"/api/catalog/products/{product_id}/variants")

    assert response.status_code == 200
    assert response.json() == {
        "id_producto": product_id,
        "nombre_producto": "Camisa Oxford",
        "tallas": ["L", "M"],
        "colores": ["Azul", "Blanco"],
        "variantes": [
            {"id_variante": 1, "sku": "OXF-M-BLA", "talla": "M", "color": "Blanco"},
            {"id_variante": 2, "sku": "OXF-L-AZU", "talla": "L", "color": "Azul"},
        ],
    }
    assert "id_talla" not in response.text
    assert "id_color" not in response.text


def test_get_product_variants_returns_empty_lists_when_product_has_no_variants(db) -> None:
    categoria = Categoria(nombre="Camisas", descripcion=None)
    producto = Producto(categoria=categoria, nombre="Camisa Lisa", descripcion=None, precio_base=Decimal("200"))
    db.add_all([categoria, producto])
    db.commit()

    response = TestClient(app).get(f"/api/catalog/products/{producto.id_producto}/variants")

    assert response.status_code == 200
    assert response.json()["tallas"] == []
    assert response.json()["colores"] == []
    assert response.json()["variantes"] == []


def test_get_product_variants_returns_not_found_for_unknown_product(db) -> None:
    response = TestClient(app).get("/api/catalog/products/999/variants")

    assert response.status_code == 404
    assert response.json()["message"] == "Producto no encontrado"


def test_product_variants_endpoint_is_documented_in_openapi() -> None:
    operation = app.openapi()["paths"]["/api/catalog/products/{id_producto}/variants"]["get"]

    assert "200" in operation["responses"]
    assert "404" in operation["responses"]
