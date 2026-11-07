from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from conftest import session_token
from app.main import app
from app.models.color import Color
from app.models.categoria import Categoria
from app.models.inventario import Inventario
from app.models.organizacion import Organizacion
from app.models.pago import Pago
from app.models.pedido import Pedido
from app.models.pedido_detalle import PedidoDetalle
from app.models.plan import Plan
from app.models.producto import Producto
from app.models.producto_variante import ProductoVariante
from app.models.reserva import Reserva
from app.models.rol import Rol
from app.models.sucursal import Sucursal
from app.models.suscripcion import Suscripcion
from app.models.talla import Talla
from app.models.usuario import Usuario


def _headers(db, role_name: str, email: str, organization_id: int = 1) -> dict[str, str]:
    role = db.scalar(select(Rol).where(Rol.nombre == role_name))
    if role is None:
        role = Rol(nombre=role_name, estado="ACTIVO")
        db.add(role)
        db.flush()
    user = Usuario(
        id_organizacion=organization_id,
        id_rol=role.id_rol,
        nombres="Métrica",
        apellidos="Test",
        correo=email,
        password_hash="not-used-in-this-test",
        estado="ACTIVO",
    )
    db.add(user)
    db.commit()
    token = session_token(db, {"id_usuario": user.id_usuario, "rol": role_name})
    return {"Authorization": f"Bearer {token}"}


def _make_order(db, *, product_variant, user_id: int, amount: str, order_date: datetime,
                payment_date: datetime, payment_state: str = "PAGADO") -> Pedido:
    order = Pedido(
        id_vendedor=user_id,
        estado="CONFIRMADO" if payment_state == "PAGADO" else "PENDIENTE",
        total=Decimal(amount),
        fecha_pedido=order_date,
    )
    db.add(order)
    db.flush()
    db.add(PedidoDetalle(pedido=order, variante=product_variant, cantidad=1,
                         precio_unitario=Decimal(amount)))
    db.add(Pago(pedido=order, metodo_pago="QR", monto=Decimal(amount), estado=payment_state,
                fecha_pago=payment_date))
    db.flush()
    return order


def _usage(client, headers, organization_id: int, start: date, end: date):
    return client.get(
        f"/api/platform/organizations/{organization_id}/usage",
        headers=headers,
        params={"desde": start.isoformat(), "hasta": end.isoformat()},
    )


def test_usage_metrics_are_period_scoped_and_isolated_between_organizations(db):
    db.info.pop("organization_id", None)
    db.add_all([
        Organizacion(id_organizacion=2, nombre="UrbanVogue", slug="urban-vogue", estado="ACTIVA"),
        Organizacion(id_organizacion=3, nombre="Elegance Boutique", slug="elegance-boutique", estado="ACTIVA"),
    ])
    admin1 = _headers(db, "ADMINISTRADOR", "usage-admin-one@example.test", 1)
    admin2 = _headers(db, "ADMINISTRADOR", "usage-admin-two@example.test", 2)
    employee = _headers(db, "ENCARGADO_SUCURSAL", "usage-employee@example.test", 1)
    customer = _headers(db, "CLIENTE", "usage-client@example.test", 1)
    platform = _headers(db, "ADMINISTRADOR_PLATAFORMA", "usage-platform@example.test", 1)
    # Add a second active and one inactive company user; names and contacts must not be returned.
    db.add_all([
        Usuario(id_organizacion=1, id_rol=db.scalar(select(Rol.id_rol).where(Rol.nombre == "ENCARGADO_SUCURSAL")),
                nombres="Otro", apellidos="Activo", correo="usage-active@example.test", password_hash="x", estado="ACTIVO"),
        Usuario(id_organizacion=1, id_rol=db.scalar(select(Rol.id_rol).where(Rol.nombre == "ENCARGADO_SUCURSAL")),
                nombres="Inactivo", apellidos="Usuario", correo="usage-inactive@example.test", password_hash="x", estado="INACTIVO"),
    ])
    category = Categoria(nombre="Métricas", descripcion="Datos de prueba", estado="ACTIVO")
    size = Talla(nombre="M", estado="ACTIVO")
    color = Color(nombre="Azul", estado="ACTIVO")
    plan1 = Plan(codigo="ESTILO", nombre="Plan Estilo", max_sucursales=2, activo=True)
    plan2 = Plan(codigo="MODA", nombre="Plan Moda", max_sucursales=10, activo=True)
    db.add_all([category, size, color, plan1, plan2])
    db.flush()

    branches = [
        Sucursal(id_organizacion=1, nombre="Central", direccion="Calle 1", ciudad="La Paz", estado="ACTIVA"),
        Sucursal(id_organizacion=1, nombre="Cerrada", direccion="Calle 2", ciudad="La Paz", estado="INACTIVA"),
        Sucursal(id_organizacion=2, nombre="Urban Central", direccion="Calle 3", ciudad="La Paz", estado="ACTIVA"),
    ]
    db.add_all(branches)
    db.flush()
    product1 = Producto(id_organizacion=1, id_categoria=category.id_categoria, nombre="Producto Uno",
                        descripcion=None, precio_base=Decimal("150"), estado="ACTIVO")
    product2 = Producto(id_organizacion=2, id_categoria=category.id_categoria, nombre="Producto Dos",
                        descripcion=None, precio_base=Decimal("900"), estado="ACTIVO")
    db.add_all([product1, product2])
    db.flush()
    variant1 = ProductoVariante(id_producto=product1.id_producto, id_talla=size.id_talla,
                                id_color=color.id_color, sku="USAGE-ONE", estado="ACTIVO")
    variant2 = ProductoVariante(id_producto=product2.id_producto, id_talla=size.id_talla,
                                id_color=color.id_color, sku="USAGE-TWO", estado="ACTIVO")
    db.add_all([variant1, variant2])
    db.flush()
    inventories = [
        Inventario(id_sucursal=branches[0].id_sucursal, id_variante=variant1.id_variante,
                   stock_disponible=5, stock_reservado=2, stock_vendido=1),
        Inventario(id_sucursal=branches[1].id_sucursal, id_variante=variant1.id_variante,
                   stock_disponible=3, stock_reservado=1, stock_vendido=0),
        Inventario(id_sucursal=branches[2].id_sucursal, id_variante=variant2.id_variante,
                   stock_disponible=100, stock_reservado=10, stock_vendido=5),
    ]
    db.add_all(inventories)
    today = date.today()
    now = datetime.combine(today, time(hour=12), tzinfo=timezone.utc)
    old = now - timedelta(days=40)
    user1_id = db.scalar(select(Usuario.id_usuario).where(Usuario.correo == "usage-admin-one@example.test"))
    user2_id = db.scalar(select(Usuario.id_usuario).where(Usuario.correo == "usage-admin-two@example.test"))
    _make_order(db, product_variant=variant1, user_id=user1_id, amount="150.00",
                order_date=now, payment_date=now)
    _make_order(db, product_variant=variant1, user_id=user1_id, amount="50.00",
                order_date=now, payment_date=now, payment_state="PENDIENTE")
    _make_order(db, product_variant=variant1, user_id=user1_id, amount="75.00",
                order_date=old, payment_date=old)
    _make_order(db, product_variant=variant2, user_id=user2_id, amount="900.00",
                order_date=now, payment_date=now)
    db.add_all([
        Reserva(id_usuario=user1_id, id_inventario=inventories[0].id_inventario, cantidad=1,
                estado="PENDIENTE", fecha=now),
        Reserva(id_usuario=user1_id, id_inventario=inventories[0].id_inventario, cantidad=1,
                estado="CANCELADA", fecha=now),
        Reserva(id_usuario=user1_id, id_inventario=inventories[0].id_inventario, cantidad=1,
                estado="PENDIENTE", fecha=old),
        Reserva(id_usuario=user2_id, id_inventario=inventories[2].id_inventario, cantidad=1,
                estado="PENDIENTE", fecha=now),
    ])
    db.add_all([
        Suscripcion(organizacion_id=1, plan=plan1, estado="ACTIVA", fecha_inicio=now - timedelta(days=5)),
        Suscripcion(organizacion_id=2, plan=plan2, estado="ACTIVA", fecha_inicio=now - timedelta(days=5)),
    ])
    db.commit()

    client = TestClient(app)
    response1 = _usage(client, platform, 1, today, today)
    response2 = _usage(client, platform, 2, today, today)
    own = client.get("/api/organizations/me/usage", headers=admin1,
                     params={"desde": today.isoformat(), "hasta": today.isoformat()})

    assert response1.status_code == 200, response1.text
    data1 = response1.json()
    assert data1["plan_codigo"] == "ESTILO"
    assert data1["estado_suscripcion"] == "ACTIVA"
    assert data1["sucursales_activas"] == 1 and data1["limite_sucursales"] == 2
    assert data1["usuarios_activos"] == 4  # admin, employee, client, and one additional active user
    assert data1["productos_registrados"] == 1
    assert data1["pedidos_periodo"] == 2
    assert Decimal(data1["ventas_periodo"]) == Decimal("150.00")
    assert data1["reservas_periodo"] == 2
    assert (data1["inventario_disponible"], data1["inventario_reservado"], data1["inventario_vendido"]) == (8, 3, 1)
    assert not ({"nombres", "apellidos", "correo", "password_hash"} & data1.keys())
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["plan_codigo"] == "MODA"
    assert data2["sucursales_activas"] == 1 and data2["limite_sucursales"] == 10
    assert data2["productos_registrados"] == 1
    assert data2["pedidos_periodo"] == 1
    assert Decimal(data2["ventas_periodo"]) == Decimal("900.00")
    assert data2["reservas_periodo"] == 1
    assert own.status_code == 200 and own.json() == data1

    all_time = client.get("/api/platform/organizations/1/usage", headers=platform)
    assert all_time.status_code == 200
    assert all_time.json()["pedidos_periodo"] == 3
    assert Decimal(all_time.json()["ventas_periodo"]) == Decimal("225.00")


def test_usage_permissions_invalid_period_and_empty_organization(db):
    db.info.pop("organization_id", None)
    db.add_all([
        Organizacion(id_organizacion=2, nombre="UrbanVogue", slug="urban-vogue", estado="ACTIVA"),
        Organizacion(id_organizacion=3, nombre="Elegance Boutique", slug="elegance-boutique", estado="ACTIVA"),
    ])
    expired_plan = Plan(codigo="EXPIRADO", nombre="Plan Expirado", max_sucursales=2, activo=True)
    db.add(expired_plan)
    db.flush()
    expired_subscription = Suscripcion(
        organizacion_id=3,
        plan=expired_plan,
        estado="ACTIVA",
        fecha_inicio=datetime.now(timezone.utc) - timedelta(days=30),
        fecha_fin=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db.add(expired_subscription)
    db.commit()
    admin = _headers(db, "ADMINISTRADOR", "usage-permission-admin@example.test", 1)
    platform = _headers(db, "ADMINISTRADOR_PLATAFORMA", "usage-permission-platform@example.test", 1)
    employee = _headers(db, "ENCARGADO_SUCURSAL", "usage-permission-employee@example.test", 1)
    client_user = _headers(db, "CLIENTE", "usage-permission-client@example.test", 1)
    client = TestClient(app)

    own = client.get("/api/platform/organizations/2/usage", headers=platform)
    assert own.status_code == 200
    empty = own.json()
    assert empty["estado_suscripcion"] == "SIN_SUSCRIPCION"
    assert empty["plan_nombre"] is None
    assert all(empty[field] == 0 for field in (
        "sucursales_activas", "usuarios_activos", "productos_registrados", "pedidos_periodo",
        "reservas_periodo", "inventario_disponible", "inventario_reservado", "inventario_vendido",
    ))
    assert Decimal(empty["ventas_periodo"]) == 0
    assert client.get("/api/platform/organizations/2/usage", headers=admin).status_code == 403
    for headers in (employee, client_user):
        assert client.get("/api/organizations/me/usage", headers=headers).status_code == 403
        assert client.get("/api/platform/organizations/1/usage", headers=headers).status_code == 403
    assert client.get("/api/platform/organizations/99/usage", headers=platform).status_code == 404
    expired_usage = client.get("/api/platform/organizations/3/usage", headers=platform)
    assert expired_usage.status_code == 200
    assert expired_usage.json()["plan_codigo"] == "EXPIRADO"
    assert expired_usage.json()["estado_suscripcion"] == "VENCIDA"
    db.refresh(expired_subscription)
    assert expired_subscription.estado == "VENCIDA"
    assert client.get("/api/platform/organizations/1/usage", headers=platform,
                      params={"desde": "2026-11-30", "hasta": "2026-11-01"}).status_code == 422
