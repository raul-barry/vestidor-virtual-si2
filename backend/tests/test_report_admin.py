from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from conftest import session_token
from app.main import app
from app.models.bitacora import Bitacora
from app.models.categoria import Categoria
from app.models.cliente import Cliente
from app.models.color import Color
from app.models.inventario import Inventario
from app.models.movimiento_inventario import MovimientoInventario
from app.models.pago import Pago
from app.models.pedido import Pedido
from app.models.pedido_detalle import PedidoDetalle
from app.models.producto import Producto
from app.models.producto_variante import ProductoVariante
from app.models.rol import Rol
from app.models.sucursal import Sucursal
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
        estado="ACTIVO",
    )
    db.add(user)
    db.commit()
    token = session_token(db, {"id_usuario": user.id_usuario, "rol": role.nombre})
    return {"Authorization": f"Bearer {token}"}, user


def create_report_data(db, admin: Usuario) -> None:
    client_role = Rol(nombre="CLIENTE", descripcion=None)
    client_user = Usuario(
        rol=client_role,
        nombres="Carlos",
        apellidos="Perez",
        correo="cliente@example.com",
        telefono="70000000",
        password_hash="hash",
        estado="ACTIVO",
    )
    client = Cliente(usuario=client_user)
    category = Categoria(nombre="Camisas", descripcion=None)
    product = Producto(categoria=category, nombre="Camisa Oxford", descripcion=None, precio_base=Decimal("250"))
    size = Talla(nombre="M")
    color = Color(nombre="Blanco")
    variant = ProductoVariante(producto=product, talla=size, color=color, sku="OXF-M-BLA")
    branch = Sucursal(nombre="Sucursal Central", direccion="Av. Principal 100")
    inventory = Inventario(sucursal=branch, variante=variant, stock_disponible=3, stock_reservado=0)
    order = Pedido(cliente=client, estado="CONFIRMADO", total=Decimal("500"))
    detail = PedidoDetalle(pedido=order, variante=variant, cantidad=2, precio_unitario=Decimal("250"))
    payment = Pago(pedido=order, metodo_pago="QR", monto=Decimal("500"), estado="APROBADO")
    movement = MovimientoInventario(
        inventario=inventory,
        tipo_movimiento="ENTRADA",
        cantidad=3,
        stock_anterior=0,
        stock_nuevo=3,
        motivo="Stock inicial",
        usuario=admin,
    )
    db.add_all([
        client_role, client_user, client, category, product, size, color, variant,
        branch, inventory, order, detail, payment, movement,
    ])
    db.commit()


def test_dashboard_and_sales_reports(db) -> None:
    headers, admin = create_headers(db, "ADMINISTRADOR", "admin@example.com")
    create_report_data(db, admin)
    client = TestClient(app)

    dashboard = client.get("/api/admin/reports/dashboard", headers=headers)
    sales = client.get("/api/admin/reports/sales", headers=headers)
    future_sales = client.get(
        f"/api/admin/reports/sales?fecha_inicio={(date.today() + timedelta(days=365)).isoformat()}",
        headers=headers,
    )

    assert dashboard.status_code == 200
    assert dashboard.json()["usuarios_totales"] == 2
    assert dashboard.json()["clientes_totales"] == 1
    assert dashboard.json()["ventas_totales"] == "500.00"
    assert dashboard.json()["productos_stock_bajo"] == 1
    assert sales.status_code == 200
    assert sales.json()["cantidad_pedidos"] == 1
    assert sales.json()["pedidos_por_estado"] == {"CONFIRMADO": 1}
    assert future_sales.json()["cantidad_pedidos"] == 0
    assert db.scalar(select(Bitacora).where(Bitacora.id_usuario == admin.id_usuario)) is not None


def test_rankings_inventory_and_customer_reports(db) -> None:
    headers, admin = create_headers(db, "ADMINISTRADOR", "admin@example.com")
    create_report_data(db, admin)
    client = TestClient(app)

    products = client.get("/api/admin/reports/top-products", headers=headers)
    categories = client.get("/api/admin/reports/top-categories", headers=headers)
    inventory = client.get("/api/admin/reports/inventory", headers=headers)
    customers = client.get("/api/admin/reports/customers", headers=headers)

    assert products.status_code == 200
    assert products.json()[0] == {
        "producto": "Camisa Oxford",
        "cantidad_vendida": 2,
        "ingresos_generados": "500.00",
    }
    assert categories.json()[0]["categoria"] == "Camisas"
    assert inventory.json()["stock_total"] == 3
    assert inventory.json()["productos_stock_bajo"] == 1
    assert inventory.json()["productos_sin_stock"] == 0
    assert inventory.json()["movimientos_recientes"][0]["tipo"] == "ENTRADA"
    assert customers.json() == {
        "usuarios_registrados": 2,
        "clientes_activos": 1,
        "clientes_nuevos_mes": 1,
        "clientes_con_compras": 1,
    }


def test_customer_cannot_access_reports(db) -> None:
    headers, _ = create_headers(db, "CLIENTE", "cliente@example.com")

    response = TestClient(app).get("/api/admin/reports/dashboard", headers=headers)

    assert response.status_code == 403
