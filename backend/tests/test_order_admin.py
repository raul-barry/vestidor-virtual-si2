from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.security import create_access_token
from app.main import app
from app.models.bitacora import Bitacora
from app.models.categoria import Categoria
from app.models.cliente import Cliente
from app.models.color import Color
from app.models.pedido import Pedido
from app.models.pedido_detalle import PedidoDetalle
from app.models.producto import Producto
from app.models.producto_variante import ProductoVariante
from app.models.rol import Rol
from app.models.talla import Talla
from app.models.usuario import Usuario


def create_headers(db, role_name: str, correo: str) -> tuple[dict[str, str], Usuario]:
    role = db.scalar(select(Rol).where(Rol.nombre == role_name))
    if role is None:
        role = Rol(nombre=role_name, descripcion=None)
        db.add(role)
        db.flush()
    user = Usuario(
        id_rol=role.id_rol,
        nombres="Admin" if role_name == "ADMINISTRADOR" else "Cliente",
        apellidos="User",
        correo=correo,
        telefono=None,
        password_hash="hash",
    )
    db.add(user)
    db.commit()
    token = create_access_token({"id_usuario": user.id_usuario, "rol": role.nombre})
    return {"Authorization": f"Bearer {token}"}, user


def create_order(db, estado: str = "PENDIENTE") -> Pedido:
    client_role = Rol(nombre="CLIENTE", descripcion=None)
    client_user = Usuario(
        rol=client_role,
        nombres="Carlos",
        apellidos="Perez",
        correo="cliente@example.com",
        telefono="70000000",
        password_hash="hash",
    )
    client = Cliente(usuario=client_user)
    category = Categoria(nombre="Camisas", descripcion=None)
    product = Producto(categoria=category, nombre="Camisa Oxford", descripcion=None, precio_base=Decimal("250"))
    size = Talla(nombre="M")
    color = Color(nombre="Blanco")
    variant = ProductoVariante(producto=product, talla=size, color=color, sku="OXF-M-BLA")
    order = Pedido(cliente=client, estado=estado, total=Decimal("500.00"))
    detail = PedidoDetalle(pedido=order, variante=variant, cantidad=2, precio_unitario=Decimal("250.00"))
    db.add_all([client_role, client_user, client, category, product, size, color, variant, order, detail])
    db.commit()
    return order


def test_admin_can_list_and_filter_orders(db) -> None:
    headers, _ = create_headers(db, "ADMINISTRADOR", "admin@example.com")
    pending_order = create_order(db)
    confirmed_order = Pedido(id_cliente=pending_order.id_cliente, estado="CONFIRMADO", total=Decimal("100"))
    db.add(confirmed_order)
    db.commit()
    client = TestClient(app)

    listed = client.get("/api/admin/orders", headers=headers)
    filtered = client.get("/api/admin/orders?estado=PENDIENTE", headers=headers)

    assert listed.status_code == 200
    assert len(listed.json()) == 2
    assert filtered.status_code == 200
    assert [order["id_pedido"] for order in filtered.json()] == [pending_order.id_pedido]


def test_admin_can_view_detail_and_change_status_with_audit(db) -> None:
    headers, admin = create_headers(db, "ADMINISTRADOR", "admin@example.com")
    order = create_order(db)
    client = TestClient(app)

    detail = client.get(f"/api/admin/orders/{order.id_pedido}", headers=headers)
    updated = client.put(
        f"/api/admin/orders/{order.id_pedido}/status",
        headers=headers,
        json={"estado": "CONFIRMADO"},
    )

    assert detail.status_code == 200
    assert detail.json()["cliente"] == "Carlos Perez"
    assert detail.json()["detalles"][0]["producto"] == "Camisa Oxford"
    assert updated.status_code == 200
    assert updated.json()["estado"] == "CONFIRMADO"
    audit = db.scalar(select(Bitacora).where(Bitacora.id_usuario == admin.id_usuario))
    assert audit is not None
    assert audit.accion == f"Pedido {order.id_pedido}: estado PENDIENTE -> CONFIRMADO"


def test_admin_cannot_apply_invalid_transition_or_access_missing_order(db) -> None:
    headers, _ = create_headers(db, "ADMINISTRADOR", "admin@example.com")
    order = create_order(db)
    client = TestClient(app)

    invalid = client.put(
        f"/api/admin/orders/{order.id_pedido}/status",
        headers=headers,
        json={"estado": "ENVIADO"},
    )
    missing = client.get("/api/admin/orders/999", headers=headers)

    assert invalid.status_code == 422
    assert invalid.json()["message"] == "Transición de estado no permitida"
    assert missing.status_code == 404


def test_customer_cannot_access_order_administration(db) -> None:
    headers, _ = create_headers(db, "CLIENTE", "cliente@example.com")

    response = TestClient(app).get("/api/admin/orders", headers=headers)

    assert response.status_code == 403
