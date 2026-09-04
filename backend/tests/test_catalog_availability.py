from decimal import Decimal

from fastapi.testclient import TestClient

from app.main import app
from app.models.categoria import Categoria
from app.models.color import Color
from app.models.inventario import Inventario
from app.models.producto import Producto
from app.models.producto_variante import ProductoVariante
from app.models.sucursal import Sucursal
from app.models.talla import Talla


def create_product_with_inventory(db) -> int:
    categoria = Categoria(nombre="Camisas", descripcion=None)
    producto = Producto(categoria=categoria, nombre="Camisa Oxford", descripcion=None, precio_base=Decimal("250"))
    talla_m = Talla(nombre="M")
    talla_l = Talla(nombre="L")
    blanco = Color(nombre="Blanco")
    azul = Color(nombre="Azul")
    central = Sucursal(nombre="Sucursal Central", direccion="Av. Principal 100")
    norte = Sucursal(nombre="Sucursal Norte", direccion="Av. Norte 250")
    variant_m = ProductoVariante(producto=producto, talla=talla_m, color=blanco, sku="OXF-M-BLA")
    variant_l = ProductoVariante(producto=producto, talla=talla_l, color=azul, sku="OXF-L-AZU")
    db.add_all(
        [
            categoria,
            producto,
            talla_m,
            talla_l,
            blanco,
            azul,
            central,
            norte,
            variant_m,
            variant_l,
            Inventario(sucursal=central, variante=variant_m, stock_disponible=3, stock_reservado=0),
            Inventario(sucursal=central, variante=variant_l, stock_disponible=2, stock_reservado=0),
            Inventario(sucursal=norte, variante=variant_m, stock_disponible=7, stock_reservado=0),
            Inventario(sucursal=norte, variante=variant_l, stock_disponible=0, stock_reservado=0),
        ]
    )
    db.commit()
    return producto.id_producto


def test_product_availability_aggregates_stock_per_branch(db) -> None:
    product_id = create_product_with_inventory(db)

    response = TestClient(app).get(f"/api/catalog/products/{product_id}/availability")

    assert response.status_code == 200
    assert response.json() == {
        "id_producto": product_id,
        "nombre_producto": "Camisa Oxford",
        "disponibilidad": [
            {
                "id_sucursal": 1,
                "nombre_sucursal": "Sucursal Central",
                "direccion": "Av. Principal 100",
                "stock_disponible": 5,
            },
            {
                "id_sucursal": 2,
                "nombre_sucursal": "Sucursal Norte",
                "direccion": "Av. Norte 250",
                "stock_disponible": 7,
            },
        ],
    }
    assert "id_variante" not in response.text


def test_product_availability_returns_empty_list_when_product_has_no_stock(db) -> None:
    categoria = Categoria(nombre="Camisas", descripcion=None)
    producto = Producto(categoria=categoria, nombre="Camisa Lisa", descripcion=None, precio_base=Decimal("200"))
    talla = Talla(nombre="M")
    color = Color(nombre="Blanco")
    sucursal = Sucursal(nombre="Sucursal Central", direccion="Av. Principal 100")
    variante = ProductoVariante(producto=producto, talla=talla, color=color, sku="LIS-M-BLA")
    db.add_all(
        [
            categoria,
            producto,
            talla,
            color,
            sucursal,
            variante,
            Inventario(sucursal=sucursal, variante=variante, stock_disponible=0, stock_reservado=0),
        ]
    )
    db.commit()

    response = TestClient(app).get(f"/api/catalog/products/{producto.id_producto}/availability")

    assert response.status_code == 200
    assert response.json()["disponibilidad"] == []


def test_product_availability_returns_not_found_for_unknown_product(db) -> None:
    response = TestClient(app).get("/api/catalog/products/999/availability")

    assert response.status_code == 404
    assert response.json()["message"] == "Producto no encontrado"


def test_product_availability_endpoint_is_documented_in_openapi() -> None:
    operation = app.openapi()["paths"]["/api/catalog/products/{id_producto}/availability"]["get"]

    assert "200" in operation["responses"]
    assert "404" in operation["responses"]
