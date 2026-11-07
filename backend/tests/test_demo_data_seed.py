from sqlalchemy import func, select, text

from app.database.demo_data_seed import ORGANIZATIONS, seed_demo_data
from app.models.carrito import Carrito
from app.models.audit_log import AuditLog
from app.models.cliente import Cliente
from app.models.inventario import Inventario
from app.models.organizacion import Organizacion
from app.models.pago import Pago
from app.models.plan import Plan
from app.models.pedido import Pedido
from app.models.producto import Producto
from app.models.reserva import Reserva
from app.models.sucursal import Sucursal
from app.models.suscripcion import Suscripcion
from app.models.usuario import Usuario
from app.models.rol import Rol


def test_demo_seed_is_idempotent_and_keeps_tenant_data_separate(db):
    password = "Synthetic-demo-passphrase-242!"
    first = seed_demo_data(db, password)
    db.commit()
    second = seed_demo_data(db, password)
    db.commit()

    assert first["organizations"] == 2
    assert first["users"] == 54
    assert first["products"] == 45
    assert first["demo_sales"] == 144
    assert second["organizations"] == 0
    assert second["users"] == 0
    assert second["products"] == 0
    assert second["demo_sales"] == 0

    db.info.pop("organization_id", None)
    organizations = {slug: db.scalar(select(Organizacion).where(Organizacion.slug == slug)) for _, slug, _, _ in ORGANIZATIONS}
    assert len({row.id_organizacion for row in organizations.values()}) == 3
    for _, slug, plan_code, branch_limit in ORGANIZATIONS:
        organization = organizations[slug]
        assert db.scalar(select(func.count(Usuario.id_usuario)).where(Usuario.id_organizacion == organization.id_organizacion)) >= 18
        synthetic_roles = dict(db.execute(select(Rol.nombre, func.count(Usuario.id_usuario)).join(
            Usuario, Usuario.id_rol == Rol.id_rol
        ).where(
            Usuario.id_organizacion == organization.id_organizacion,
            Usuario.correo.like(f"{slug}.%@demo.test"),
        ).group_by(Rol.nombre)).all())
        assert synthetic_roles == {
            "ADMINISTRADOR": 1, "ENCARGADO_SUCURSAL": 2, "CAJERO": 2,
            "EMPLEADO": 3, "CLIENTE": 10,
        }
        assert db.scalar(select(func.count(Producto.id_producto)).where(Producto.id_organizacion == organization.id_organizacion)) == 15
        assert db.scalar(select(func.count(Sucursal.id_sucursal)).where(
            Sucursal.id_organizacion == organization.id_organizacion,
            Sucursal.estado == "ACTIVA",
        )) <= branch_limit
        assert db.scalar(select(func.count(Suscripcion.id_suscripcion)).where(
            Suscripcion.organizacion_id == organization.id_organizacion,
            Suscripcion.estado == "ACTIVA",
        )) == 1
        assert db.scalar(select(func.count(Inventario.id_inventario)).join(Sucursal).where(
            Sucursal.id_organizacion == organization.id_organizacion
        )) > 0
        active_plan = db.scalar(select(Plan.codigo).join(
            Suscripcion, Suscripcion.plan_id == Plan.id_plan
        ).where(Suscripcion.organizacion_id == organization.id_organizacion, Suscripcion.estado == "ACTIVA"))
        assert active_plan == plan_code
        assert db.scalar(select(func.count(Carrito.id_carrito)).join(
            Cliente, Carrito.id_cliente == Cliente.id_cliente
        ).join(Usuario, Cliente.id_usuario == Usuario.id_usuario).where(
            Usuario.id_organizacion == organization.id_organizacion
        )) == 3
        assert db.scalar(select(func.count(Reserva.id_reserva)).join(
            Usuario, Reserva.id_usuario == Usuario.id_usuario
        ).where(Usuario.id_organizacion == organization.id_organizacion, Reserva.estado == "PENDIENTE")) == 2
        misplaced_branch_user = db.scalar(select(Usuario.id_usuario).join(
            Sucursal, Usuario.id_sucursal == Sucursal.id_sucursal
        ).where(
            Usuario.id_organizacion == organization.id_organizacion,
            Sucursal.id_organizacion != organization.id_organizacion,
        ).limit(1))
        assert misplaced_branch_user is None

    # Each synthetic order and payment remains tenant-owned through customer, seller, and branch links.
    for organization in organizations.values():
        orders = db.scalars(select(Pedido).where(
            Pedido.referencia_entrega.like(f"DEMO-SEED:{organization.slug}:SALE:%")
        )).all()
        assert len(orders) in (36, 54)
        assert all(order.estado == "CONFIRMADO" for order in orders)
        assert all(order.id_cliente is not None and order.id_sucursal_entrega is not None for order in orders)
        assert all(db.scalar(select(Pago.id_pago).where(Pago.id_pedido == order.id_pedido, Pago.estado == "PAGADO")) for order in orders)

    assert db.scalar(select(func.count(AuditLog.id))) == 0
    assert db.execute(text("PRAGMA foreign_key_check")).all() == []


def test_demo_seed_requires_explicit_non_default_password(db):
    import pytest

    with pytest.raises(ValueError, match="at least 12"):
        seed_demo_data(db, "short")
