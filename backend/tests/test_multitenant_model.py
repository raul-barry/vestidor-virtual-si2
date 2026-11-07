import pytest
from sqlalchemy.exc import IntegrityError

from app.models.organizacion import Organizacion
from app.models.categoria import Categoria
from app.models.producto import Producto
from app.models.sucursal import Sucursal
from app.models.color import Color
from app.models.talla import Talla
from app.models.producto_variante import ProductoVariante
from app.models.inventario import Inventario
from sqlalchemy import select


def test_same_branch_name_is_allowed_for_different_organizations(db):
    first = db.get(Organizacion, 1)
    first_branch = Sucursal(nombre="Central", direccion="Dirección A", organizacion=first)
    db.add(first_branch)
    db.commit()
    second = Organizacion(nombre="Otra empresa", slug="otra-empresa", estado="ACTIVA")
    db.add(second)
    db.flush()
    db.info["organization_id"] = second.id_organizacion
    db.add(Sucursal(nombre="Central", direccion="Dirección B", organizacion=second))
    db.commit()

    db.info.pop("organization_id")
    assert [branch.nombre for branch in first.sucursales] == ["Central"]
    assert [branch.nombre for branch in second.sucursales] == ["Central"]


def test_duplicate_branch_name_within_organization_is_rejected(db):
    db.add_all([
        Sucursal(nombre="Central", direccion="Dirección A", id_organizacion=1),
        Sucursal(nombre="Central", direccion="Dirección B", id_organizacion=1),
    ])
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_branch_requires_an_existing_organization(db):
    db.connection().exec_driver_sql("PRAGMA foreign_keys=ON")
    db.add(Sucursal(nombre="Sin organización", direccion="Dirección", id_organizacion=999))
    with pytest.raises(ValueError, match="no coincide"):
        db.commit()
    db.rollback()


def test_product_queries_are_isolated_for_three_organizations(db):
    orgs = [
        Organizacion(nombre="UrbanVogue", slug="urbanvogue", estado="ACTIVA"),
        Organizacion(nombre="Elegance Boutique", slug="elegance-boutique", estado="ACTIVA"),
    ]
    db.add_all(orgs)
    category = Categoria(nombre="Compartida", descripcion="Dato global")
    db.add(category)
    db.flush()
    products = [(1, "FS item"), (orgs[0].id_organizacion, "UV item"), (orgs[1].id_organizacion, "EB item")]
    for organization_id, name in products:
        db.info["organization_id"] = organization_id
        db.add(Producto(id_organizacion=organization_id, id_categoria=category.id_categoria,
                        nombre=name, precio_base=10, estado="ACTIVO"))
        db.flush()
    for organization_id, expected in products:
        db.info["organization_id"] = organization_id
        assert [row.nombre for row in db.scalars(select(Producto)).all()] == [expected]


def test_inventory_cannot_join_a_branch_and_variant_from_different_organizations(db):
    urban = Organizacion(nombre="UrbanVogue", slug="urbanvogue", estado="ACTIVA")
    db.add(urban)
    category = Categoria(nombre="Ropa", descripcion="Global")
    size, color = Talla(nombre="M"), Color(nombre="Negro")
    db.add_all([category, size, color])
    db.flush()
    db.info["organization_id"] = 1
    branch = Sucursal(nombre="Central", direccion="Centro", id_organizacion=1)
    store_product = Producto(id_organizacion=1, id_categoria=category.id_categoria, nombre="Local", precio_base=10)
    db.add_all([branch, store_product])
    db.flush()
    db.info["organization_id"] = urban.id_organizacion
    external_product = Producto(id_organizacion=urban.id_organizacion, id_categoria=category.id_categoria,
                                nombre="Externo", precio_base=10)
    db.add(external_product)
    db.flush()
    variant = ProductoVariante(id_producto=external_product.id_producto, id_talla=size.id_talla,
                               id_color=color.id_color, sku="UV-001")
    db.add(variant)
    db.flush()
    branch_id, variant_id = branch.id_sucursal, variant.id_variante
    db.expunge_all()
    db.info["organization_id"] = 1
    db.add(Inventario(id_sucursal=branch_id, id_variante=variant_id, stock_disponible=1))
    with pytest.raises(ValueError, match="no pertenece"):
        db.flush()
    db.rollback()
