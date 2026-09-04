from decimal import Decimal

from sqlalchemy import select

from app.database.catalog_seed import (
    INITIAL_BRANCHES,
    INITIAL_CATEGORIES,
    INITIAL_COLORS,
    INITIAL_SIZES,
    seed_catalog_data,
)
from app.models.categoria import Categoria
from app.models.color import Color
from app.models.inventario import Inventario
from app.models.producto import Producto
from app.models.producto_variante import ProductoVariante
from app.models.sucursal import Sucursal
from app.models.talla import Talla


def test_catalog_models_preserve_required_relationships(db) -> None:
    categoria = Categoria(nombre="Camisas de prueba", descripcion="Categoría de prueba")
    producto = Producto(
        categoria=categoria,
        nombre="Camisa Oxford",
        descripcion="Camisa de prueba",
        precio_base=Decimal("199.90"),
    )
    talla = Talla(nombre="M-prueba")
    color = Color(nombre="Azul-prueba")
    variante = ProductoVariante(producto=producto, talla=talla, color=color, sku="CAM-OXF-M-AZU")
    sucursal = Sucursal(nombre="Sucursal de prueba", direccion="Dirección de prueba")
    inventario = Inventario(sucursal=sucursal, variante=variante, stock_disponible=10, stock_reservado=0)
    db.add_all([categoria, producto, talla, color, variante, sucursal, inventario])
    db.flush()

    assert categoria.id_categoria is not None
    assert producto.categoria == categoria
    assert producto.variantes == [variante]
    assert variante.talla == talla
    assert variante.color == color
    assert inventario.sucursal == sucursal
    assert inventario.variante == variante
    assert sucursal.inventarios == [inventario]


def test_catalog_seed_is_idempotent(db) -> None:
    created = seed_catalog_data(db)
    db.commit()

    assert created == {
        "categorias": len(INITIAL_CATEGORIES),
        "tallas": len(INITIAL_SIZES),
        "colores": len(INITIAL_COLORS),
        "sucursales": len(INITIAL_BRANCHES),
    }
    assert set(db.scalars(select(Categoria.nombre)).all()) == set(INITIAL_CATEGORIES)
    assert set(db.scalars(select(Talla.nombre)).all()) == set(INITIAL_SIZES)
    assert set(db.scalars(select(Color.nombre)).all()) == set(INITIAL_COLORS)
    assert set(db.scalars(select(Sucursal.nombre)).all()) == {
        name for name, _ in INITIAL_BRANCHES
    }
    assert seed_catalog_data(db) == {"categorias": 0, "tallas": 0, "colores": 0, "sucursales": 0}
