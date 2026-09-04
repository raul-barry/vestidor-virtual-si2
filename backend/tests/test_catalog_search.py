from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.categoria import Categoria
from app.models.color import Color
from app.models.producto import Producto
from app.models.producto_variante import ProductoVariante
from app.models.talla import Talla


def create_catalog_data(db) -> TestClient:
    camisas = Categoria(nombre="Camisas", descripcion=None)
    pantalones = Categoria(nombre="Pantalones", descripcion=None)
    talla_m = Talla(nombre="M")
    talla_l = Talla(nombre="L")
    blanco = Color(nombre="Blanco")
    azul = Color(nombre="Azul")
    negro = Color(nombre="Negro")
    oxford = Producto(categoria=camisas, nombre="Camisa Oxford", descripcion=None, precio_base=Decimal("250"))
    lino = Producto(categoria=camisas, nombre="Camisa Lino", descripcion=None, precio_base=Decimal("350"))
    chino = Producto(categoria=pantalones, nombre="Pantalón Chino", descripcion=None, precio_base=Decimal("300"))
    db.add_all(
        [
            camisas,
            pantalones,
            talla_m,
            talla_l,
            blanco,
            azul,
            negro,
            oxford,
            lino,
            chino,
            ProductoVariante(producto=oxford, talla=talla_m, color=blanco, sku="OXF-M-BLA"),
            ProductoVariante(producto=lino, talla=talla_l, color=azul, sku="LIN-L-AZU"),
            ProductoVariante(producto=chino, talla=talla_m, color=negro, sku="CHI-M-NEG"),
        ]
    )
    db.commit()
    return TestClient(app)


@pytest.mark.parametrize(
    ("params", "expected_names"),
    [
        ({"nombre": "camisa"}, {"Camisa Oxford", "Camisa Lino"}),
        ({"categoria": "Camisas"}, {"Camisa Oxford", "Camisa Lino"}),
        ({"talla": "M"}, {"Camisa Oxford", "Pantalón Chino"}),
        ({"color": "Blanco"}, {"Camisa Oxford"}),
        ({"precio_max": "300"}, {"Camisa Oxford", "Pantalón Chino"}),
        (
            {"categoria": "Camisas", "talla": "L", "color": "Azul", "precio_max": "400"},
            {"Camisa Lino"},
        ),
    ],
)
def test_search_catalog_filters_products(db, params, expected_names) -> None:
    response = create_catalog_data(db).get("/api/catalog/products/search", params=params)

    assert response.status_code == 200
    assert {product["nombre"] for product in response.json()} == expected_names
    assert all({"categoria", "variantes"}.issubset(product) for product in response.json())


def test_search_catalog_without_filters_returns_complete_catalog(db) -> None:
    response = create_catalog_data(db).get("/api/catalog/products/search")

    assert response.status_code == 200
    assert len(response.json()) == 3


def test_search_catalog_without_results_returns_empty_list(db) -> None:
    response = create_catalog_data(db).get("/api/catalog/products/search", params={"nombre": "inexistente"})

    assert response.status_code == 200
    assert response.json() == []


def test_search_catalog_rejects_non_positive_price(db) -> None:
    response = TestClient(app).get("/api/catalog/products/search", params={"precio_max": "0"})

    assert response.status_code == 422


def test_search_catalog_is_documented_in_openapi() -> None:
    operation = app.openapi()["paths"]["/api/catalog/products/search"]["get"]

    assert {parameter["name"] for parameter in operation["parameters"]} == {
        "nombre",
        "categoria",
        "talla",
        "color",
        "precio_max",
    }
    assert "200" in operation["responses"]
