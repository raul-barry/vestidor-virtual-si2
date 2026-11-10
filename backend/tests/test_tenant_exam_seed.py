import secrets

from sqlalchemy import func, select

import pytest

from app.core.config import settings
from app.core.security import verify_password
from app.database.plan_seed import seed_commercial_plans
from app.database.seed import seed_roles
from app.database.tenant_exam_seed import (
    SeedPreflightError,
    _fixture_is_complete,
    apply_tenant_seed,
    audit_tenant_seeded_data,
    dry_run_report,
)
from app.database.tenant_exam_seed import _user_manifest
from app.database import tenant_exam_seed as tenant_exam_seed_module
from app.services.platform_admin_bootstrap import bootstrap_platform_admin
from app.database.tenant_exam_seed_data import ROLE_NAMES, TENANTS
from app.models.cliente import Cliente
from app.models.exchange import GarmentExchange
from app.models.inventario import Inventario
from app.models.loyalty import LoyaltyAccount, LoyaltyLedger, LoyaltyProgram
from app.models.organizacion import Organizacion
from app.models.pago import Pago
from app.models.pedido import Pedido
from app.models.plan import Plan
from app.models.producto import Producto
from app.models.producto_variante import ProductoVariante
from app.models.reserva import Reserva
from app.models.rol import Rol
from app.models.sucursal import Sucursal
from app.models.suscripcion import Suscripcion
from app.models.usuario import Usuario


SEED_PASSWORD = secrets.token_urlsafe(24)


def _prepare(db, monkeypatch):
    monkeypatch.setattr(settings, "environment", "test")
    monkeypatch.setattr(settings, "payment_simulation_mode", True)
    seed_roles(db, ROLE_NAMES)
    seed_commercial_plans(db)
    db.commit()


def _counts(db):
    models = (
        Organizacion, Sucursal, Usuario, Cliente, Producto, ProductoVariante,
        Inventario, Pedido, Pago, Reserva, GarmentExchange, Suscripcion,
        LoyaltyProgram, LoyaltyAccount, LoyaltyLedger,
    )
    return tuple(db.scalar(select(func.count()).select_from(model)) for model in models)


def test_tenant_exam_seed_dry_run_is_read_only_and_honors_estilo_branch_limit(db, monkeypatch):
    _prepare(db, monkeypatch)
    before = _counts(db)

    report = dry_run_report(db)

    assert report["mode"] == "DRY RUN"
    assert report["writes_database"] is False
    assert report["blockers"] == []
    assert report["expected_totals"]["organizations"] == 4
    assert db.info["organization_id"] == 1
    distrito = next(row for row in report["tenants"] if row["slug"] == "distrito-urbano")
    assert distrito["active_branch_count"] == 2
    assert [(branch["name"], branch["active"]) for branch in distrito["branches"]] == [
        ("Centro", True), ("Plan 3000", True), ("La Ramada", False),
    ]
    assert _counts(db) == before


def test_tenant_exam_seed_creates_isolated_demo_data_and_is_idempotent(db, monkeypatch):
    _prepare(db, monkeypatch)
    platform_admin, created = bootstrap_platform_admin(
        db, "superadmin.saas@vestidor.com", secrets.token_urlsafe(24),
    )
    assert created is True
    assert platform_admin.id_organizacion is None
    db.commit()

    first = apply_tenant_seed(db, SEED_PASSWORD)
    after_first = _counts(db)
    diagnostics = []
    assert _fixture_is_complete(db, diagnostics), diagnostics
    second = apply_tenant_seed(db, SEED_PASSWORD)

    assert first["writes_database"] is True
    assert second["writes_database"] is False
    assert second["already_seeded"] is True
    assert _counts(db) == after_first
    db.info.pop("organization_id", None)
    audit = audit_tenant_seeded_data(db)
    assert audit["blockers"] == []
    assert len(audit["tenants"]) == 4
    assert audit["platform_administrators"]["count"] == 1
    assert audit["platform_administrators"]["global_accounts"][0]["organization_id"] is None
    assert {row["slug"] for row in audit["tenants"]} >= {"magnolia-boutique", "atelier-sur"}
    assert all(row["cu12_ok"] and row["cu13_ok"] for row in audit["tenants"])
    assert sum(row["roles"]["ADMINISTRADOR"] for row in audit["tenants"]) == 4
    assert sum(row["roles"]["ENCARGADO_SUCURSAL"] for row in audit["tenants"]) == 14
    assert sum(row["roles"]["CAJERO"] for row in audit["tenants"]) == 14
    assert sum(row["roles"]["CLIENTE"] for row in audit["tenants"]) == 146
    assert all(
        row["roles"]["ADMINISTRADOR"] == 1
        and row["roles"]["ENCARGADO_SUCURSAL"] == row["branches"]["total"]
        and row["roles"]["CAJERO"] == row["branches"]["total"]
        for row in audit["tenants"]
    )
    assert all(
        user["email"].endswith("@vestidor.com")
        for user in first["user_manifest"]
    )
    assert len(TENANTS) == 4
    for spec in TENANTS:
        organization = db.scalar(select(Organizacion).where(Organizacion.slug == spec.slug))
        assert organization is not None
        branches = list(db.scalars(select(Sucursal).where(
            Sucursal.id_organizacion == organization.id_organizacion
        )).all())
        assert len(branches) == len(spec.branches)
        active = [branch for branch in branches if branch.estado == "ACTIVA"]
        plan = db.scalar(select(Plan).where(Plan.codigo == spec.plan_code))
        assert plan is not None
        assert plan.max_sucursales is None or len(active) <= plan.max_sucursales

        products = list(db.scalars(select(Producto).where(
            Producto.id_organizacion == organization.id_organizacion
        )).all())
        assert len(products) == len(spec.products)
        assert all(product.variantes for product in products)
        users = list(db.scalars(select(Usuario).where(
            Usuario.id_organizacion == organization.id_organizacion
        )).all())
        assert all(user.correo.endswith("@vestidor.com") for user in users)
        assert verify_password(SEED_PASSWORD, users[0].password_hash)
        assert all(user.id_rol != db.scalar(select(Rol.id_rol).where(
            Rol.nombre == "ADMINISTRADOR_PLATAFORMA"
        )) for user in users)

        customers = list(db.scalars(select(Cliente).join(Usuario).where(
            Usuario.id_organizacion == organization.id_organizacion
        )).all())
        assert len(customers) == spec.customer_count
        orders = list(db.scalars(select(Pedido).join(Cliente).where(
            Cliente.id_cliente == Pedido.id_cliente,
            Cliente.id_usuario.in_([customer.id_usuario for customer in customers]),
        )).all())
        assert len([order for order in orders if order.estado in {"ENTREGADO", "CONFIRMADO"}]) == spec.paid_sales
        paid_order_ids = {order.id_pedido for order in orders if order.estado in {"ENTREGADO", "CONFIRMADO"}}
        payments = list(db.scalars(select(Pago).where(Pago.id_pedido.in_(paid_order_ids))).all())
        assert len(payments) == len(paid_order_ids)
        assert all(payment.estado == "PAGADO" for payment in payments)

        reservations = list(db.scalars(select(Reserva).join(Pedido).join(Cliente).where(
            Cliente.id_usuario.in_([customer.id_usuario for customer in customers]),
        )).all())
        assert len(reservations) == spec.reservation_count
        exchanges = list(db.scalars(select(GarmentExchange).where(
            GarmentExchange.organization_id == organization.id_organizacion,
        )).all())
        assert len(exchanges) == spec.exchange_scenarios
        assert all(exchange.organization_id == organization.id_organizacion for exchange in exchanges)
        subscription = db.scalar(select(Suscripcion).where(
            Suscripcion.organizacion_id == organization.id_organizacion,
            Suscripcion.estado == "ACTIVA",
        ))
        assert subscription.plan_id == plan.id_plan
        inventories = list(db.scalars(select(Inventario).join(Sucursal).where(
            Sucursal.id_organizacion == organization.id_organizacion,
        )).all())
        assert all(min(item.stock_disponible, item.stock_reservado, item.stock_vendido) >= 0
                   for item in inventories)

    district = db.scalar(select(Organizacion).where(Organizacion.slug == "distrito-urbano"))
    ramada = db.scalar(select(Sucursal).where(
        Sucursal.id_organizacion == district.id_organizacion, Sucursal.nombre == "La Ramada",
    ))
    assert ramada.estado == "INACTIVA"
    assert not db.scalar(select(func.count()).select_from(Pedido).where(
        Pedido.id_sucursal_entrega == ramada.id_sucursal,
    ))

    glamour_org_ids = [row.id_organizacion for row in db.scalars(select(Organizacion).where(
        Organizacion.slug.in_(["magnolia-boutique", "atelier-sur"])
    )).all()]
    programs = list(db.scalars(select(LoyaltyProgram).where(
        LoyaltyProgram.organization_id.in_(glamour_org_ids)
    )).all())
    assert len(programs) == 2
    assert db.scalar(select(func.count()).select_from(LoyaltyProgram).where(
        LoyaltyProgram.organization_id == district.id_organizacion,
    )) == 0


def test_tenant_seed_hashes_a_distinct_password_for_each_account(db, monkeypatch):
    _prepare(db, monkeypatch)
    monkeypatch.setattr(
        tenant_exam_seed_module,
        "hash_password",
        lambda password: f"test-hash:{password}",
    )
    identities = [row for spec in TENANTS for row in _user_manifest(spec)]
    passwords = {
        str(row["email"]): f"Unique-Seed-Password-{index:04d}!"
        for index, row in enumerate(identities)
    }

    report = apply_tenant_seed(db, passwords)
    # The tenant-scoped session filter is left on the last seeded organization.
    # Clear it before asserting the cross-tenant account manifest as a whole.
    db.info.pop("organization_id", None)
    accounts = list(db.scalars(select(Usuario).where(
        Usuario.correo.in_(passwords.keys()),
    )).all())

    assert len(accounts) == 182
    assert len({passwords[user.correo] for user in accounts}) == 182
    assert all(user.password_hash == f"test-hash:{passwords[user.correo]}" for user in accounts)
    assert report["password_source"] == "manifiesto privado individual (valores nunca incluidos)"


def test_tenant_exam_seed_preflight_rejects_short_password_without_writes(db, monkeypatch):
    _prepare(db, monkeypatch)
    before = _counts(db)

    try:
        apply_tenant_seed(db, "short")
    except SeedPreflightError as exc:
        assert "12" in str(exc)
    else:
        raise AssertionError("Expected short password preflight failure")

    assert _counts(db) == before


def test_render_production_override_requires_verified_postgresql_target(db, monkeypatch):
    from app.database.render_seed_safety import APPROVED_RENDER_POSTGRES_ID

    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "payment_simulation_mode", False)
    db.info["verified_render_postgres_id"] = APPROVED_RENDER_POSTGRES_ID
    before = _counts(db)

    with pytest.raises(SeedPreflightError, match="PostgreSQL"):
        apply_tenant_seed(
            db, SEED_PASSWORD, allow_render_production=True,
            seed_shared_master_data=False,
        )

    assert _counts(db) == before
