from decimal import Decimal

import pytest

from app.core.exceptions import AppException
from app.models.categoria import Categoria
from app.models.cliente import Cliente
from app.models.color import Color
from app.models.producto import Producto
from app.models.producto_variante import ProductoVariante
from app.models.rol import Rol
from app.models.talla import Talla
from app.models.usuario import Usuario
from app.services.cart_service import CartService


def create_client_and_variant(db) -> tuple[int, int]:
    role = Rol(nombre="CLIENTE", descripcion=None)
    usuario = Usuario(
        rol=role,
        nombres="Carlos",
        apellidos="Perez",
        correo="cliente@example.com",
        telefono="70000000",
        password_hash="hash",
    )
    cliente = Cliente(usuario=usuario)
    categoria = Categoria(nombre="Camisas", descripcion=None)
    producto = Producto(
        categoria=categoria,
        nombre="Camisa Oxford",
        descripcion=None,
        precio_base=Decimal("250.00"),
    )
    talla = Talla(nombre="M")
    color = Color(nombre="Blanco")
    variante = ProductoVariante(producto=producto, talla=talla, color=color, sku="OXF-M-BLA")
    db.add_all([role, usuario, cliente, categoria, producto, talla, color, variante])
    db.flush()
    return cliente.id_cliente, variante.id_variante


def test_get_cart_creates_an_active_cart_for_client_without_one(db) -> None:
    client_id, _ = create_client_and_variant(db)

    cart = CartService(db).get_cart(client_id)

    assert cart.estado == "ACTIVO"
    assert cart.items == []
    assert cart.total == Decimal("0")


def test_add_product_creates_item_and_calculates_total(db) -> None:
    client_id, variant_id = create_client_and_variant(db)

    cart = CartService(db).add_product(client_id, variant_id, 2)

    assert len(cart.items) == 1
    assert cart.items[0].producto == "Camisa Oxford"
    assert cart.items[0].talla == "M"
    assert cart.items[0].color == "Blanco"
    assert cart.items[0].cantidad == 2
    assert cart.items[0].precio_unitario == Decimal("250.00")
    assert cart.total == Decimal("500.00")


def test_update_item_quantity(db) -> None:
    client_id, variant_id = create_client_and_variant(db)
    service = CartService(db)
    cart = service.add_product(client_id, variant_id, 1)

    updated_cart = service.update_item_quantity(client_id, cart.items[0].id_detalle, 3)

    assert updated_cart.items[0].cantidad == 3
    assert updated_cart.total == Decimal("750.00")


def test_remove_item_keeps_cart_and_removes_detail(db) -> None:
    client_id, variant_id = create_client_and_variant(db)
    service = CartService(db)
    cart = service.add_product(client_id, variant_id, 1)

    updated_cart = service.remove_item(client_id, cart.items[0].id_detalle)

    assert updated_cart.id_carrito == cart.id_carrito
    assert updated_cart.items == []
    assert updated_cart.total == Decimal("0")


def test_add_product_rejects_unknown_variant(db) -> None:
    client_id, _ = create_client_and_variant(db)

    with pytest.raises(AppException, match="Variante no encontrada"):
        CartService(db).add_product(client_id, 999, 1)
