from decimal import Decimal

import pytest

from app.core.exceptions import AppException
from app.models.carrito import Carrito
from app.models.categoria import Categoria
from app.models.cliente import Cliente
from app.models.color import Color
from app.models.producto import Producto
from app.models.producto_variante import ProductoVariante
from app.models.rol import Rol
from app.models.talla import Talla
from app.models.usuario import Usuario
from app.services.cart_service import CartService
from app.services.order_service import OrderService


def create_client(db, role: Rol, correo: str) -> Cliente:
    usuario = Usuario(
        rol=role,
        nombres="Carlos",
        apellidos="Perez",
        correo=correo,
        telefono="70000000",
        password_hash="hash",
    )
    cliente = Cliente(usuario=usuario)
    db.add_all([usuario, cliente])
    db.flush()
    return cliente


def create_variant(db) -> tuple[Producto, ProductoVariante]:
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
    db.add_all([categoria, producto, talla, color, variante])
    db.flush()
    return producto, variante


def test_create_order_copies_cart_items_calculates_total_and_finalizes_cart(db) -> None:
    role = Rol(nombre="CLIENTE", descripcion=None)
    db.add(role)
    db.flush()
    client = create_client(db, role, "cliente@example.com")
    product, variant = create_variant(db)
    cart = CartService(db).add_item(client.id_cliente, variant.id_variante, 2)
    product.precio_base = Decimal("300.00")
    db.commit()

    order = OrderService(db).create_order_from_cart(client.id_cliente)

    assert order.estado == "PENDIENTE"
    assert order.total == Decimal("500.00")
    assert len(order.detalles) == 1
    assert order.detalles[0].producto == "Camisa Oxford"
    assert order.detalles[0].cantidad == 2
    assert order.detalles[0].precio_unitario == Decimal("250.00")
    saved_cart = db.get(Carrito, cart.id_carrito)
    assert saved_cart is not None
    db.refresh(saved_cart)
    assert saved_cart.estado == "FINALIZADO"


def test_client_can_only_view_own_orders(db) -> None:
    role = Rol(nombre="CLIENTE", descripcion=None)
    db.add(role)
    db.flush()
    first_client = create_client(db, role, "primero@example.com")
    second_client = create_client(db, role, "segundo@example.com")
    _, variant = create_variant(db)
    CartService(db).add_item(first_client.id_cliente, variant.id_variante, 1)
    first_order = OrderService(db).create_order_from_cart(first_client.id_cliente)
    CartService(db).add_item(second_client.id_cliente, variant.id_variante, 1)
    OrderService(db).create_order_from_cart(second_client.id_cliente)

    client_orders = OrderService(db).get_client_orders(first_client.id_cliente)

    assert [order.id_pedido for order in client_orders] == [first_order.id_pedido]
    with pytest.raises(AppException, match="Pedido no encontrado"):
        OrderService(db).get_order_detail(second_client.id_cliente, first_order.id_pedido)
