"""Safe, idempotent synthetic data seeder for the four second-partial tenants.

This module never runs migrations, calls a payment gateway, sends notifications,
or writes to the offline synchronization outbox. Call ``dry_run_report`` for a
read-only preview and ``apply_tenant_seed`` only with an isolated/test database.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import re
import unicodedata
from collections.abc import Mapping
from uuid import NAMESPACE_URL, uuid5

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.core.config import settings
from app.core.security import hash_password
from app.database.tenant_exam_seed_data import (
    CATEGORY_DESCRIPTIONS,
    COLOR_NAMES,
    CUSTOMERS,
    ROLE_NAMES,
    SIZE_NAMES,
    STAFF,
    TENANTS,
    TenantSpec,
)
from app.models.audit_log import AuditLog
from app.models.cliente import Cliente
from app.models.comercio import Coleccion, Devolucion, Proveedor
from app.models.categoria import Categoria
from app.models.color import Color
from app.models.inventario import Inventario
from app.models.exchange import GarmentExchange
from app.models.loyalty import LoyaltyAccount, LoyaltyLedger, LoyaltyProgram, LoyaltyTier
from app.models.movimiento_inventario import MovimientoInventario
from app.models.organizacion import Organizacion
from app.models.pago import Pago
from app.models.pedido import Pedido
from app.models.pedido_detalle import PedidoDetalle
from app.models.plan import Plan, PlanCaracteristica
from app.models.producto import Producto
from app.models.producto_variante import ProductoVariante
from app.models.recurso_virtual import RecursoVirtual
from app.models.reserva import Reserva
from app.models.rol import Rol
from app.models.sucursal import Sucursal
from app.models.suscripcion import Suscripcion
from app.models.talla import Talla
from app.models.usuario import Usuario
from app.services.exchange_service import create_customer_request
from app.services.loyalty_service import LoyaltyService
from app.services.payment_providers import (
    QRPaymentProvider,
    SimulatedStripeCardPaymentProvider,
)
from app.services.payment_service import PaymentService
from app.services.pricing_service import current_price
from app.services.subscription_service import SubscriptionService
from app.services.sync_handlers import SyncActor
from app.services.pos_sync_handler import create_offline_pos_sale
from app.schemas.payment import CreatePaymentRequest


class SeedPreflightError(ValueError):
    """The database cannot safely accept the requested tenant fixture."""


@dataclass
class _Counts:
    tenants: int = 0
    branches: int = 0
    users: int = 0
    customers: int = 0
    categories: int = 0
    products: int = 0
    variants: int = 0
    inventories: int = 0
    opening_movements: int = 0
    paid_sales: int = 0
    cancelled_orders: int = 0
    reservations: int = 0
    exchange_scenarios: int = 0
    subscriptions: int = 0
    loyalty_programs: int = 0
    loyalty_accounts: int = 0
    loyalty_movements: int = 0


@dataclass
class _Sale:
    order: Pedido
    details: list[PedidoDetalle]
    branch: Sucursal | None


_ADMINISTRATORS = {
    "magnolia-boutique": ("Adriana Lucía", "Paz"),
    "punto-nativo": ("Mauricio Andrés", "Roca"),
    "distrito-urbano": ("Gabriela Elena", "Montaño"),
    "atelier-sur": ("Valentina María", "Céspedes"),
}
_CASH_RESERVED_STATES = ("PENDIENTE", "CONFIRMADA", "CANCELADA", "VENCIDA", "COMPLETADA")
_IMAGE_ROOT = Path(__file__).resolve().parents[1] / "assets" / "catalog"


def _ascii(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", ".", value.lower()).strip(".")


def _brand_tag(spec: TenantSpec) -> str:
    return spec.slug.replace("-", ".")


def _admin_email(spec: TenantSpec) -> str:
    return f"administracion.{_brand_tag(spec)}@vestidor.com"


def _staff_specs(spec: TenantSpec) -> list[tuple[str, str, str, int]]:
    result: list[tuple[str, str, str, int]] = []
    for branch_index, _branch in enumerate(spec.branches):
        manager_first, manager_last, manager_role = STAFF[branch_index]
        result.append((manager_first, manager_last, manager_role, branch_index))
        cashier_first, cashier_last, cashier_role = STAFF[4 + branch_index]
        result.append((cashier_first, cashier_last, cashier_role, branch_index))
    active_branch_index = next(index for index, branch in enumerate(spec.branches) if branch.active)
    first, last, role = STAFF[-1]
    result.append((first, last, role, active_branch_index))
    return result


def _customer_email(spec: TenantSpec, names: tuple[str, str]) -> str:
    return f"{_ascii(' '.join(names))}.cliente.{_brand_tag(spec)}@vestidor.com"


def _staff_email(spec: TenantSpec, names: tuple[str, str], role: str) -> str:
    role_tag = {
        "ENCARGADO_SUCURSAL": "encargado",
        "CAJERO": "caja",
        "EMPLEADO": "equipo",
    }[role]
    return f"{_ascii(' '.join(names))}.{role_tag}.{_brand_tag(spec)}@vestidor.com"


def _user_manifest(spec: TenantSpec) -> list[dict[str, str | None]]:
    admin_first, admin_last = _ADMINISTRATORS[spec.slug]
    rows: list[dict[str, str | None]] = [{
        "organization": spec.name, "name": f"{admin_first} {admin_last}",
        "email": _admin_email(spec), "username": _admin_email(spec),
        "role": "ADMINISTRADOR", "branch": None,
        "password_source": "FASHIONSTORE_SEED_PASSWORD",
    }]
    branches = spec.branches
    for first, last, role, branch_index in _staff_specs(spec):
        email = _staff_email(spec, (first, last), role)
        rows.append({
            "organization": spec.name, "name": f"{first} {last}", "email": email,
            "username": email, "role": role, "branch": branches[branch_index].name,
            "password_source": "FASHIONSTORE_SEED_PASSWORD",
        })
    for names in CUSTOMERS[:spec.customer_count]:
        email = _customer_email(spec, names)
        rows.append({
            "organization": spec.name, "name": f"{names[0]} {names[1]}", "email": email,
            "username": email, "role": "CLIENTE", "branch": None,
            "password_source": "FASHIONSTORE_SEED_PASSWORD",
        })
    return rows


def _plan_for(db: Session, code: str) -> Plan | None:
    return db.scalar(select(Plan).where(Plan.codigo == code))


def dry_run_report(db: Session) -> dict:
    """Read-only target preview while preserving any caller tenant scope."""
    marker = object()
    previous_scope = db.info.pop("organization_id", marker)
    try:
        return _dry_run_report_unscoped(db)
    finally:
        if previous_scope is not marker:
            db.info["organization_id"] = previous_scope


def _dry_run_report_unscoped(db: Session) -> dict:
    """Read-only target preview and safety checks; performs no flush or commit."""
    missing_roles = sorted(set(ROLE_NAMES) - set(db.scalars(
        select(Rol.nombre).where(Rol.nombre.in_(ROLE_NAMES))
    ).all()))
    required_categories = sorted({product.category for spec in TENANTS for product in spec.products})
    shared_master_missing = {
        "roles": missing_roles,
        "categories": sorted(set(required_categories) - set(db.scalars(
            select(Categoria.nombre).where(Categoria.nombre.in_(required_categories))
        ).all())),
        "sizes": sorted(set(SIZE_NAMES) - set(db.scalars(
            select(Talla.nombre).where(Talla.nombre.in_(SIZE_NAMES))
        ).all())),
        "colors": sorted(set(COLOR_NAMES) - set(db.scalars(
            select(Color.nombre).where(Color.nombre.in_(COLOR_NAMES))
        ).all())),
    }
    blockers: list[str] = []
    tenants: list[dict] = []
    all_emails: set[str] = set()
    for spec in TENANTS:
        plan = _plan_for(db, spec.plan_code)
        organization = db.scalar(select(Organizacion).where(Organizacion.slug == spec.slug))
        if plan is None or not plan.activo:
            blockers.append(f"No existe un plan activo {spec.plan_code}.")
        existing_branches: list[Sucursal] = []
        if organization is not None:
            if organization.nombre != spec.name:
                blockers.append(f"El slug {spec.slug} ya pertenece a otra empresa.")
            existing_branches = list(db.scalars(select(Sucursal).where(
                Sucursal.id_organizacion == organization.id_organizacion
            )).all())
            expected_names = {item.name for item in spec.branches}
            unexpected = sorted(row.nombre for row in existing_branches if row.nombre not in expected_names)
            if unexpected:
                blockers.append(f"{spec.slug} ya contiene sucursales ajenas al seeder: {', '.join(unexpected)}.")
            anchor = db.scalar(select(Usuario).where(Usuario.correo == _admin_email(spec)))
            if anchor is None or anchor.id_organizacion != organization.id_organizacion:
                blockers.append(f"El slug {spec.slug} ya existe y no tiene el administrador ancla del seeder.")
            active_subscription = db.scalar(select(Suscripcion).where(
                Suscripcion.organizacion_id == organization.id_organizacion,
                Suscripcion.estado == "ACTIVA",
            ))
            if active_subscription is not None and plan is not None and active_subscription.plan_id != plan.id_plan:
                blockers.append(f"{spec.slug} ya tiene otra suscripción activa; el seeder no la reemplazará.")
        desired_active = sum(1 for item in spec.branches if item.active)
        if plan is not None and plan.max_sucursales is not None and desired_active > plan.max_sucursales:
            blockers.append(
                f"{spec.slug}: {desired_active} sucursales activas exceden el límite "
                f"{plan.max_sucursales} del plan {spec.plan_code}."
            )
        if plan is not None and plan.max_sucursales is not None and organization is not None:
            final_active = sum(1 for item in spec.branches if item.active)
            if final_active > plan.max_sucursales:
                blockers.append(f"{spec.slug} excedería el límite de sucursales del plan.")
        manifest = _user_manifest(spec)
        for row in manifest:
            email = str(row["email"])
            if email in all_emails:
                blockers.append(f"Correo repetido en la configuración: {email}.")
            all_emails.add(email)
            existing_user = db.scalar(select(Usuario).where(Usuario.correo == email))
            if existing_user is not None and (
                organization is None or existing_user.id_organizacion != organization.id_organizacion
            ):
                blockers.append(f"El correo requerido ya pertenece a otro registro: {email}.")
        features: dict[str, bool] = {}
        if plan is not None:
            features = {
                row.codigo: row.habilitada
                for row in db.scalars(select(PlanCaracteristica).where(
                    PlanCaracteristica.plan_id == plan.id_plan
                )).all()
            }
        tenants.append({
            "name": spec.name,
            "slug": spec.slug,
            "plan": spec.plan_code,
            "branches": [asdict(item) for item in spec.branches],
            "active_branch_count": desired_active,
            "customer_count": spec.customer_count,
            "staff_count": len(_staff_specs(spec)),
            "administrator_count": 1,
            "product_count": len(spec.products),
            "variants_per_product": "6 (3 tallas × 2 colores)",
            "paid_sales_target": spec.paid_sales,
            "reservation_target": spec.reservation_count,
            "exchange_scenario_target": spec.exchange_scenarios,
            "loyalty_enabled_by_current_plan": bool(features.get("fidelizacion_clientes", False)),
            "existing_organization": organization is not None,
            "users": manifest,
        })
    expected_tables = {
        "organizations": len(TENANTS),
        "branches": sum(len(spec.branches) for spec in TENANTS),
        "active_branches": sum(len(spec.active_branches) for spec in TENANTS),
        "administrators": len(TENANTS),
        "staff": sum(len(_staff_specs(spec)) for spec in TENANTS),
        "customers": sum(spec.customer_count for spec in TENANTS),
        "products": sum(len(spec.products) for spec in TENANTS),
        "paid_sales": sum(spec.paid_sales for spec in TENANTS),
        "reservations": sum(spec.reservation_count for spec in TENANTS),
        "exchange_scenarios": sum(spec.exchange_scenarios for spec in TENANTS),
    }
    return {"mode": "DRY RUN", "writes_database": False, "expected_totals": expected_tables,
            "roles_to_create": missing_roles,
            "shared_master_data": {"modified": False, "missing": shared_master_missing},
            "tenants": tenants, "blockers": list(dict.fromkeys(blockers))}


def audit_tenant_seeded_data(db: Session) -> dict:
    """Read-only counts, tenant integrity checks, CU12, and CU13 branch coverage."""
    from sqlalchemy.orm import aliased

    marker = object()
    previous_scope = db.info.pop("organization_id", marker)
    tenant_reports: list[dict] = []
    blockers: list[str] = []
    try:
        roles = {row.nombre: row.id_rol for row in db.scalars(select(Rol)).all()}
        role_names = ("ADMINISTRADOR", "ENCARGADO_SUCURSAL", "CAJERO", "EMPLEADO", "CLIENTE")
        for spec in TENANTS:
            organization = db.scalar(select(Organizacion).where(Organizacion.slug == spec.slug))
            if organization is None:
                blockers.append(f"No existe la organización {spec.slug}.")
                continue
            org_id = organization.id_organizacion

            def count(statement) -> int:
                return int(db.scalar(statement) or 0)

            users_by_role = {
                name: count(select(func.count()).select_from(Usuario).where(
                    Usuario.id_organizacion == org_id,
                    Usuario.id_rol == roles.get(name, -1),
                )) for name in role_names
            }
            branches = list(db.scalars(select(Sucursal).where(
                Sucursal.id_organizacion == org_id,
            ).order_by(Sucursal.nombre)).all())
            products_count = count(select(func.count()).select_from(Producto).where(
                Producto.id_organizacion == org_id,
            ))
            variants_count = count(select(func.count()).select_from(ProductoVariante).join(Producto).where(
                Producto.id_organizacion == org_id,
            ))
            inventory_count = count(select(func.count()).select_from(Inventario).join(Sucursal).join(
                ProductoVariante, ProductoVariante.id_variante == Inventario.id_variante,
            ).join(Producto).where(
                Sucursal.id_organizacion == org_id, Producto.id_organizacion == org_id,
            ))
            movement_count = count(select(func.count()).select_from(MovimientoInventario).join(
                Inventario, Inventario.id_inventario == MovimientoInventario.id_inventario,
            ).join(Sucursal).join(
                ProductoVariante, ProductoVariante.id_variante == Inventario.id_variante,
            ).join(Producto).where(
                Sucursal.id_organizacion == org_id, Producto.id_organizacion == org_id,
            ))
            customer_user = aliased(Usuario)
            seller_user = aliased(Usuario)
            tenant_order_source = select(Pedido.id_pedido).join(
                Cliente, Cliente.id_cliente == Pedido.id_cliente,
            ).join(customer_user, customer_user.id_usuario == Cliente.id_usuario).where(
                customer_user.id_organizacion == org_id,
            )
            sales_count = count(select(func.count()).select_from(Pedido).where(
                Pedido.id_pedido.in_(tenant_order_source),
                Pedido.estado.in_(("ENTREGADO", "CONFIRMADO")),
            ))
            payments_count = count(select(func.count()).select_from(Pago).join(
                Pedido, Pedido.id_pedido == Pago.id_pedido,
            ).where(Pedido.id_pedido.in_(tenant_order_source)))
            paid_payments_count = count(select(func.count()).select_from(Pago).join(
                Pedido, Pedido.id_pedido == Pago.id_pedido,
            ).where(Pedido.id_pedido.in_(tenant_order_source), Pago.estado == "PAGADO"))
            reservations_count = count(select(func.count()).select_from(Reserva).join(
                Usuario, Usuario.id_usuario == Reserva.id_usuario,
            ).where(Usuario.id_organizacion == org_id))
            exchanges_count = count(select(func.count()).select_from(GarmentExchange).where(
                GarmentExchange.organization_id == org_id,
            ))
            subscription = db.scalar(select(Suscripcion).where(
                Suscripcion.organizacion_id == org_id, Suscripcion.estado == "ACTIVA",
            ).order_by(Suscripcion.id_suscripcion.desc()))
            plan = db.get(Plan, subscription.plan_id) if subscription else None
            plan_loyalty = bool(plan and _tenant_feature(db, plan, "fidelizacion_clientes"))
            loyalty_programs = count(select(func.count()).select_from(LoyaltyProgram).where(
                LoyaltyProgram.organization_id == org_id,
            ))
            loyalty_accounts = count(select(func.count()).select_from(LoyaltyAccount).where(
                LoyaltyAccount.organization_id == org_id,
            ))
            loyalty_movements = count(select(func.count()).select_from(LoyaltyLedger).where(
                LoyaltyLedger.organization_id == org_id,
            ))
            branch_sales = []
            for branch in branches:
                branch_sales.append({
                    "name": branch.nombre,
                    "active": branch.estado.upper() == "ACTIVA",
                    "paid_sales": count(select(func.count()).select_from(Pedido).where(
                        Pedido.id_sucursal_entrega == branch.id_sucursal,
                        Pedido.id_pedido.in_(tenant_order_source),
                        Pedido.estado.in_(("ENTREGADO", "CONFIRMADO")),
                    )),
                })

            mismatched_stock = count(select(func.count()).select_from(Inventario).join(
                Sucursal, Sucursal.id_sucursal == Inventario.id_sucursal,
            ).join(ProductoVariante, ProductoVariante.id_variante == Inventario.id_variante).join(
                Producto, Producto.id_producto == ProductoVariante.id_producto,
            ).where(
                or_(Sucursal.id_organizacion == org_id, Producto.id_organizacion == org_id),
                Sucursal.id_organizacion != Producto.id_organizacion,
            ))
            mismatched_sellers = count(select(func.count()).select_from(Pedido).join(
                Cliente, Cliente.id_cliente == Pedido.id_cliente,
            ).join(customer_user, customer_user.id_usuario == Cliente.id_usuario).join(
                seller_user, seller_user.id_usuario == Pedido.id_vendedor,
            ).where(
                customer_user.id_organizacion == org_id,
                seller_user.id_organizacion != org_id,
            ))
            mismatched_reservations = count(select(func.count()).select_from(Reserva).join(
                Usuario, Usuario.id_usuario == Reserva.id_usuario,
            ).join(Inventario, Inventario.id_inventario == Reserva.id_inventario).join(
                Sucursal, Sucursal.id_sucursal == Inventario.id_sucursal,
            ).where(
                or_(Usuario.id_organizacion == org_id, Sucursal.id_organizacion == org_id),
                Usuario.id_organizacion != Sucursal.id_organizacion,
            ))
            mismatched_exchanges = count(select(func.count()).select_from(GarmentExchange).join(
                Cliente, Cliente.id_cliente == GarmentExchange.customer_id,
            ).join(Usuario, Usuario.id_usuario == Cliente.id_usuario).where(
                GarmentExchange.organization_id == org_id,
                Usuario.id_organizacion != org_id,
            ))
            active_branch_count = sum(1 for branch in branches if branch.estado.upper() == "ACTIVA")
            branch_coverage = sum(1 for row in branch_sales if row["active"] and row["paid_sales"] > 0)
            isolation = {
                "inventory_branch_product_mismatches": mismatched_stock,
                "customer_seller_tenant_mismatches": mismatched_sellers,
                "reservation_branch_customer_mismatches": mismatched_reservations,
                "exchange_customer_tenant_mismatches": mismatched_exchanges,
            }
            if any(isolation.values()):
                blockers.append(f"Se detectó cruce de tenant en {spec.slug}.")
            if plan is None:
                blockers.append(f"{spec.slug} no tiene suscripción activa verificable.")
            elif plan.max_sucursales is not None and active_branch_count > plan.max_sucursales:
                blockers.append(f"{spec.slug} supera el límite de sucursales activas del plan.")
            if plan_loyalty and (loyalty_programs != 1 or loyalty_accounts != users_by_role["CLIENTE"]):
                blockers.append(f"La cobertura CU12 de {spec.slug} está incompleta.")
            if not plan_loyalty and loyalty_programs:
                blockers.append(f"Hay programa CU12 en un tenant sin la característica habilitada: {spec.slug}.")
            if branch_coverage < min(2, active_branch_count):
                blockers.append(f"La cobertura de ventas por sucursal CU13 está incompleta en {spec.slug}.")
            tenant_reports.append({
                "name": spec.name, "slug": spec.slug, "organization_id": org_id,
            "roles": users_by_role,
            "permissions_by_role": {
                name: sorted(permission.codigo for permission in db.scalar(
                    select(Rol).where(Rol.nombre == name)
                ).permisos) if name in roles else []
                for name in role_names
            },
                "customers": count(select(func.count()).select_from(Cliente).join(
                    Usuario, Usuario.id_usuario == Cliente.id_usuario,
                ).where(Usuario.id_organizacion == org_id)),
                "branches": {"total": len(branches), "active": active_branch_count,
                             "paid_sales_coverage": branch_coverage, "by_branch": branch_sales},
                "products": products_count, "variants": variants_count,
                "inventories": inventory_count, "inventory_movements": movement_count,
                "paid_sales": sales_count, "payments": payments_count,
                "paid_payments": paid_payments_count, "reservations": reservations_count,
                "exchange_requests": exchanges_count,
                "loyalty": {"feature_enabled_by_plan": plan_loyalty,
                            "programs": loyalty_programs, "accounts": loyalty_accounts,
                            "ledger_movements": loyalty_movements},
                "cu12_ok": (not plan_loyalty or (loyalty_programs == 1 and loyalty_accounts == users_by_role["CLIENTE"])),
                "cu13_ok": branch_coverage >= min(2, active_branch_count),
                "isolation": isolation,
            })
        platform_role_id = db.scalar(select(Rol.id_rol).where(
            Rol.nombre == "ADMINISTRADOR_PLATAFORMA",
        ))
        platform_admins = list(db.scalars(select(Usuario).where(
            Usuario.id_rol == platform_role_id,
        )).all()) if platform_role_id is not None else []
        return {"mode": "READ-ONLY AUDIT", "writes_database": False,
                "platform_administrators": {
                    "count": len(platform_admins),
                    "global_accounts": [
                        {"email": user.correo, "organization_id": user.id_organizacion,
                         "role": user.rol.nombre, "active": user.estado.upper() == "ACTIVO"}
                        for user in platform_admins
                    ],
                },
                "tenants": tenant_reports, "blockers": list(dict.fromkeys(blockers))}
    finally:
        if previous_scope is not marker:
            db.info["organization_id"] = previous_scope


def _assert_preflight(
    report: dict, password: str | Mapping[str, str], *, allow_render_production: bool,
    seed_shared_master_data: bool,
) -> None:
    expected_emails = {
        str(row["email"]) for spec in TENANTS for row in _user_manifest(spec)
    }
    if isinstance(password, str):
        valid_passwords = len(password) >= 12 and len(password) <= 128
        unique_passwords = True
    elif isinstance(password, Mapping):
        values_are_valid = all(
            isinstance(value, str) and 20 <= len(value) <= 128
            for value in password.values()
        )
        valid_passwords = (
            set(password) == expected_emails
            and values_are_valid
        )
        unique_passwords = (
            values_are_valid and len(set(password.values())) == len(password)
        )
    else:
        valid_passwords = False
        unique_passwords = False
    if not valid_passwords:
        raise SeedPreflightError(
            "Las cuentas requieren contraseñas válidas: 12–128 caracteres para el "
            "modo local o 20–128 para el manifiesto privado individual."
        )
    if not unique_passwords:
        raise SeedPreflightError("Cada cuenta debe tener una contraseña inicial única.")
    local_environment = settings.environment.lower() in {"development", "test"}
    if not local_environment and not (allow_render_production and settings.environment.lower() == "production"):
        raise SeedPreflightError("APPLY local solo se permite en development/test; production requiere el modo Render controlado.")
    if not settings.payment_simulation_mode and not allow_render_production:
        raise SeedPreflightError("Los pagos de muestra requieren PAYMENT_SIMULATION_MODE habilitado.")
    if report["blockers"]:
        raise SeedPreflightError("Preflight bloqueado: " + " | ".join(report["blockers"]))
    if not seed_shared_master_data:
        missing = report["shared_master_data"]["missing"]
        if any(missing.values()):
            raise SeedPreflightError("Faltan datos maestros globales ya existentes: " + json.dumps(missing, ensure_ascii=False))
    missing_assets = [i for i in range(1, 6) if not (_IMAGE_ROOT / f"catalog-prenda-{i}.png").is_file()]
    if missing_assets:
        raise SeedPreflightError("Faltan assets de catálogo locales: " + ", ".join(map(str, missing_assets)))


def apply_tenant_seed(
    db: Session,
    password: str | Mapping[str, str],
    *,
    allow_render_production: bool = False,
    seed_shared_master_data: bool = True,
) -> dict:
    """Create all four tenants in one transaction; repeat runs add no duplicates."""
    if allow_render_production:
        from app.database.render_seed_safety import APPROVED_RENDER_POSTGRES_ID

        if settings.environment.lower() != "production" or db.get_bind().dialect.name != "postgresql":
            raise SeedPreflightError("El modo de producción Render exige production y PostgreSQL.")
        if db.info.get("verified_render_postgres_id") != APPROVED_RENDER_POSTGRES_ID:
            raise SeedPreflightError("Falta la verificación del destino Render aprobado.")
    report = dry_run_report(db)
    _assert_preflight(
        report, password, allow_render_production=allow_render_production,
        seed_shared_master_data=seed_shared_master_data,
    )
    if _fixture_is_complete(db):
        return {
            "mode": "APPLY",
            "writes_database": False,
            "already_seeded": True,
            "tenants": {spec.slug: asdict(_Counts()) for spec in TENANTS},
            "user_manifest": [row for spec in TENANTS for row in _user_manifest(spec)],
            "password_source": "FASHIONSTORE_SEED_PASSWORD (valor nunca incluido)",
        }
    # Finish read-only preflight work before opening the write transaction.
    db.rollback()
    if isinstance(password, Mapping):
        password_hashes = {
            email: hash_password(value) for email, value in password.items()
        }
    else:
        shared_hash = hash_password(password)
        password_hashes = {
            str(row["email"]): shared_hash
            for spec in TENANTS for row in _user_manifest(spec)
        }
    counts_by_tenant: dict[str, dict[str, int]] = {}
    previous_info = dict(db.info)
    db.info["skip_business_audit"] = True
    try:
        with db.begin():
            from app.database.seed import seed_roles

            if seed_shared_master_data:
                seed_roles(db, ROLE_NAMES)
            for tenant_index, spec in enumerate(TENANTS):
                db.info.pop("organization_id", None)
                counts = _Counts()
                organization = _get_or_create_organization(db, spec)
                db.info["organization_id"] = organization.id_organizacion
                db.info["audit_actor_role"] = "SISTEMA"
                users, branches = _seed_identity(db, spec, organization, password_hashes, counts)
                plan = _plan_for(db, spec.plan_code)
                if plan is None:
                    raise SeedPreflightError(f"No existe plan {spec.plan_code}.")
                subscription = db.scalar(select(Suscripcion).where(
                    Suscripcion.organizacion_id == organization.id_organizacion,
                    Suscripcion.estado == "ACTIVA",
                ))
                if subscription is None:
                    SubscriptionService(db).assign(
                        organization.id_organizacion, plan.id_plan, users["ADMINISTRADOR"].id_usuario,
                        commit=False,
                    )
                    counts.subscriptions += 1
                elif subscription.plan_id != plan.id_plan:
                    raise SeedPreflightError(f"La suscripción activa de {spec.slug} no coincide con el plan esperado.")
                products, variants, inventories = _seed_catalog(
                    db, spec, organization, branches, users, counts,
                    allow_shared_master_seed=seed_shared_master_data,
                )
                loyalty_active = _seed_loyalty_program(db, spec, organization, plan, users, counts)
                operational_branches = [
                    branch for branch, branch_spec in zip(branches, spec.branches)
                    if branch_spec.active
                ]
                completed_reservations = _seed_reservations(
                    db, spec, organization, operational_branches, users, products, variants, inventories, counts,
                )
                paid_sales = list(completed_reservations)
                paid_sales.extend(_seed_paid_sales(
                    db, spec, organization, operational_branches, users, products, variants, inventories,
                    spec.paid_sales - len(completed_reservations), counts,
                ))
                _seed_cancelled_scenarios(
                    db, spec, organization, operational_branches, users, products, variants, counts,
                )
                _seed_exchanges(db, spec, organization, operational_branches, paid_sales, variants, inventories, counts)
                if loyalty_active:
                    _seed_loyalty_adjustments(db, spec, organization, users, paid_sales, inventories, counts)
                _assert_tenant_invariants(db, spec, organization, branches, variants, inventories, paid_sales)
                counts.tenants = 1
                counts.branches = len(branches)
                counts_by_tenant[spec.slug] = asdict(counts)
        db.info.clear()
        db.info.update(previous_info)
    except Exception:
        db.rollback()
        db.info.clear()
        db.info.update(previous_info)
        raise
    return {"mode": "APPLY", "writes_database": True,
            "tenants": counts_by_tenant, "user_manifest": [
                row for spec in TENANTS for row in _user_manifest(spec)
            ],
            "password_source": (
                "manifiesto privado individual (valores nunca incluidos)"
                if isinstance(password, Mapping)
                else "FASHIONSTORE_SEED_PASSWORD (valor nunca incluido)"
            )}


def _fixture_is_complete(db: Session, diagnostics: list[str] | None = None) -> bool:
    marker = object()
    previous_scope = db.info.pop("organization_id", marker)
    try:
        return _fixture_is_complete_unscoped(db, diagnostics)
    finally:
        if previous_scope is not marker:
            db.info["organization_id"] = previous_scope


def _fixture_is_complete_unscoped(db: Session, diagnostics: list[str] | None = None) -> bool:
    def incomplete(slug: str, check: str) -> bool:
        if diagnostics is not None:
            diagnostics.append(f"{slug}: {check}")
        return False

    for spec in TENANTS:
        organization = db.scalar(select(Organizacion).where(Organizacion.slug == spec.slug))
        if organization is None:
            return incomplete(spec.slug, "organización")
        organization_id = organization.id_organizacion
        if db.scalar(select(func.count()).select_from(Sucursal).where(
            Sucursal.id_organizacion == organization_id,
        )) != len(spec.branches):
            return incomplete(spec.slug, "sucursales")
        expected_users = _user_manifest(spec)
        if db.scalar(select(func.count()).select_from(Usuario).where(
            Usuario.id_organizacion == organization_id,
            Usuario.correo.in_([str(item["email"]) for item in expected_users]),
        )) != len(expected_users):
            return incomplete(spec.slug, "usuarios")
        if db.scalar(select(func.count()).select_from(Producto).where(
            Producto.id_organizacion == organization_id,
            Producto.nombre.in_([item.name for item in spec.products]),
        )) != len(spec.products):
            return incomplete(spec.slug, "productos")
        completed_reservations = max(1, spec.reservation_count // 9)
        sale_marker_count = spec.paid_sales - completed_reservations
        sale_markers = [f"SEED:{spec.slug}:SALE:{index + 1:04d}"
                        for index in range(sale_marker_count)]
        if db.scalar(select(func.count()).select_from(Pedido).where(
            Pedido.referencia_entrega.in_(sale_markers),
        )) != sale_marker_count:
            return incomplete(spec.slug, f"ventas marcadas ({sale_marker_count})")
        reservation_markers = [f"SEED:{spec.slug}:RESERVATION:{index + 1:02d}"
                               for index in range(spec.reservation_count)]
        if db.scalar(select(func.count()).select_from(Reserva).join(Pedido).where(
            Pedido.referencia_entrega.in_(reservation_markers),
        )) != spec.reservation_count:
            return incomplete(spec.slug, "reservas")
        exchange_markers = [str(uuid5(NAMESPACE_URL, f"fashionstore-seed-exchange:{spec.slug}:{index + 1}"))
                            for index in range(spec.exchange_scenarios)]
        if db.scalar(select(func.count()).select_from(GarmentExchange).where(
            GarmentExchange.organization_id == organization_id,
            GarmentExchange.operation_uuid.in_(exchange_markers),
        )) != spec.exchange_scenarios:
            return incomplete(spec.slug, "cambios")
        plan = _plan_for(db, spec.plan_code)
        if plan is None or db.scalar(select(func.count()).select_from(Suscripcion).where(
            Suscripcion.organizacion_id == organization_id,
            Suscripcion.estado == "ACTIVA", Suscripcion.plan_id == plan.id_plan,
        )) != 1:
            return incomplete(spec.slug, "suscripción")
    return True


def _get_or_create_organization(db: Session, spec: TenantSpec) -> Organizacion:
    existing = db.scalar(select(Organizacion).where(Organizacion.slug == spec.slug))
    if existing is not None:
        if existing.nombre != spec.name or existing.estado.upper() != "ACTIVA":
            raise SeedPreflightError(f"La empresa {spec.slug} existe con datos incompatibles; no se modifica.")
        return existing
    from app.schemas.organization_admin import OrganizationCreate
    from app.services.organization_admin_service import OrganizationAdminService

    admin_first, admin_last = _ADMINISTRATORS[spec.slug]
    data = OrganizationCreate(
        nombre=spec.name, slug=spec.slug, razon_social=spec.name,
        correo_contacto=_admin_email(spec), telefono_contacto="+591 700 000 000",
        direccion=f"Santa Cruz de la Sierra, Bolivia — {spec.specialty}",
    )
    OrganizationAdminService(db).create_organization(data, commit=False)
    organization = db.scalar(select(Organizacion).where(Organizacion.slug == spec.slug))
    if organization is None:
        raise RuntimeError(f"No se pudo crear {spec.name}.")
    return organization


def _ensure_user(
    db: Session,
    *,
    organization: Organizacion,
    email: str,
    first: str,
    last: str,
    role: Rol,
    password_hash: str,
    branch_id: int | None,
    phone: str,
    counts: _Counts,
) -> Usuario:
    user = db.scalar(select(Usuario).where(Usuario.correo == email))
    if user is not None:
        if (user.id_organizacion != organization.id_organizacion or user.id_rol != role.id_rol
                or user.nombres != first or user.apellidos != last or user.id_sucursal != branch_id):
            raise SeedPreflightError(f"La cuenta {email} existe con datos incompatibles; no se modifica.")
        return user
    user = Usuario(
        id_organizacion=organization.id_organizacion, id_sucursal=branch_id,
        id_rol=role.id_rol, nombres=first, apellidos=last, correo=email,
        telefono=phone, password_hash=password_hash, estado="ACTIVO",
    )
    db.add(user)
    db.flush([user])
    counts.users += 1
    return user


def _seed_identity(
    db: Session, spec: TenantSpec, organization: Organizacion,
    password_hashes: Mapping[str, str], counts: _Counts,
) -> tuple[dict[str, object], list[Sucursal]]:
    roles = {row.nombre: row for row in db.scalars(select(Rol).where(Rol.nombre.in_(ROLE_NAMES))).all()}
    if set(ROLE_NAMES) - set(roles):
        raise SeedPreflightError("No se pudieron preparar los roles requeridos.")
    branches: list[Sucursal] = []
    for branch_spec in spec.branches:
        branch = db.scalar(select(Sucursal).where(
            Sucursal.id_organizacion == organization.id_organizacion,
            Sucursal.nombre == branch_spec.name,
        ))
        if branch is None:
            branch = Sucursal(
                id_organizacion=organization.id_organizacion,
                nombre=branch_spec.name, direccion=branch_spec.address,
                ciudad="Santa Cruz", estado="ACTIVA" if branch_spec.active else "INACTIVA",
            )
            db.add(branch)
            db.flush([branch])
        elif branch.direccion != branch_spec.address or branch.estado.upper() != (
            "ACTIVA" if branch_spec.active else "INACTIVA"
        ):
            raise SeedPreflightError(f"La sucursal {spec.slug}/{branch_spec.name} difiere del fixture; no se modifica.")
        branches.append(branch)
    admin_first, admin_last = _ADMINISTRATORS[spec.slug]
    admin = _ensure_user(
        db, organization=organization, email=_admin_email(spec), first=admin_first,
        last=admin_last, role=roles["ADMINISTRADOR"], password_hash=password_hashes[_admin_email(spec)],
        branch_id=None, phone="+591 700 100 001", counts=counts,
    )
    users: dict[str, object] = {"ADMINISTRADOR": admin, "CLIENTE": []}
    for index, (first, last, role_name, branch_index) in enumerate(_staff_specs(spec)):
        branch = branches[branch_index]
        staff = _ensure_user(
            db, organization=organization,
            email=_staff_email(spec, (first, last), role_name), first=first, last=last,
            role=roles[role_name], password_hash=password_hashes[
                _staff_email(spec, (first, last), role_name)
            ],
            branch_id=branch.id_sucursal, phone=f"+591 700 20{index:02d} 0{tenant_phone_suffix(spec)}",
            counts=counts,
        )
        users.setdefault(role_name, []).append(staff)
    for index, names in enumerate(CUSTOMERS[:spec.customer_count]):
        email = _customer_email(spec, names)
        customer_user = _ensure_user(
            db, organization=organization, email=email, first=names[0], last=names[1],
            role=roles["CLIENTE"], password_hash=password_hashes[email], branch_id=None,
            phone=f"+591 700 {30 + index:03d} {10 + (index * 7) % 89:02d}", counts=counts,
        )
        customer = db.scalar(select(Cliente).where(Cliente.id_usuario == customer_user.id_usuario))
        if customer is None:
            customer = Cliente(id_usuario=customer_user.id_usuario, estado="ACTIVO")
            db.add(customer)
            db.flush([customer])
            counts.customers += 1
        elif customer.estado.upper() != "ACTIVO":
            raise SeedPreflightError(f"El cliente {email} está inactivo; no se cambia.")
        _seed_customer_preferences(db, customer, index)
        users["CLIENTE"].append(customer_user)
    return users, branches


def tenant_phone_suffix(spec: TenantSpec) -> str:
    return f"{sum(ord(ch) for ch in spec.slug) % 90 + 10:02d}"


def _seed_customer_preferences(db: Session, customer: Cliente, index: int) -> None:
    from app.models.preferencia_cliente import PreferenciaCliente, PreferenciaClienteColor

    preference = db.scalar(select(PreferenciaCliente).where(
        PreferenciaCliente.id_cliente == customer.id_cliente
    ))
    if preference is None:
        preference = PreferenciaCliente(
            id_cliente=customer.id_cliente,
            talla_superior=("S", "M", "L", "XS", "M")[index % 5],
            talla_pantalon=("36", "38", "40", "34", "42")[index % 5],
            estilos=("minimalista", "casual", "ejecutivo", "urbano", "romántico")[index % 5],
        )
        db.add(preference)
        db.flush([preference])
    colors = list(db.scalars(select(Color).order_by(Color.id_color)).all())
    if not colors:
        return
    selected = (colors[index % len(colors)], colors[(index * 3 + 1) % len(colors)])
    for color in selected:
        exists = db.get(PreferenciaClienteColor, (preference.id_preferencia, color.id_color))
        if exists is None:
            db.add(PreferenciaClienteColor(
                id_preferencia=preference.id_preferencia, id_color=color.id_color,
            ))


def _named(db: Session, model, name: str, *, allow_create: bool = True, **values):
    row = db.scalar(select(model).where(model.nombre == name))
    if row is not None:
        return row, False
    if not allow_create:
        raise SeedPreflightError(f"Falta el dato maestro compartido {model.__name__}/{name}; no se crea en Render.")
    row = model(nombre=name, **values)
    db.add(row)
    db.flush([row])
    return row, True


def _seed_catalog(
    db: Session, spec: TenantSpec, organization: Organizacion, branches: list[Sucursal],
    users: dict[str, object], counts: _Counts, *, allow_shared_master_seed: bool,
) -> tuple[list[Producto], dict[int, list[ProductoVariante]], dict[tuple[int, int], Inventario]]:
    categories: dict[str, Categoria] = {}
    for name in sorted({product.category for product in spec.products}):
        row, created = _named(
            db, Categoria, name,
            allow_create=allow_shared_master_seed,
            descripcion=CATEGORY_DESCRIPTIONS.get(name, f"Prendas de la categoría {name}."),
        )
        categories[name] = row
        counts.categories += int(created)
    sizes: dict[str, Talla] = {}
    for name in SIZE_NAMES:
        sizes[name], _ = _named(db, Talla, name, allow_create=allow_shared_master_seed)
    colors: dict[str, Color] = {}
    for name in COLOR_NAMES:
        colors[name], _ = _named(db, Color, name, allow_create=allow_shared_master_seed)
    for index, user in enumerate(users["CLIENTE"]):
        _seed_customer_preferences(
            db,
            db.scalar(select(Cliente).where(Cliente.id_usuario == user.id_usuario)),
            index,
        )
    brand = spec.slug.split("-")[0][:4].upper()
    supplier_name = f"Textiles {spec.name}"
    supplier = db.scalar(select(Proveedor).where(
        Proveedor.id_organizacion == organization.id_organizacion,
        Proveedor.nombre == supplier_name,
    ))
    if supplier is None:
        supplier = Proveedor(
            id_organizacion=organization.id_organizacion,
            nombre=supplier_name, contacto=f"Compras {spec.name}",
            descripcion=f"Proveedor de telas y confección para {spec.name}.",
            persona_contacto="María Fernanda Rojas", telefono="+591 700 400 501",
            correo=f"textiles.{_brand_tag(spec)}@vestidor.com",
            direccion="Parque Industrial, Santa Cruz de la Sierra", estado="ACTIVO",
        )
        db.add(supplier)
        db.flush([supplier])
    collection_name = f"Colección {spec.name} 2026"
    collection = db.scalar(select(Coleccion).where(
        Coleccion.id_organizacion == organization.id_organizacion,
        Coleccion.nombre == collection_name,
    ))
    if collection is None:
        collection = Coleccion(
            id_organizacion=organization.id_organizacion, nombre=collection_name,
            descripcion=f"Selección de temporada: {spec.specialty.lower()}.",
            temporada="Primavera-Verano", anio=2026, estado="ACTIVO",
        )
        db.add(collection)
        db.flush([collection])
    products: list[Producto] = []
    variants_by_product: dict[int, list[ProductoVariante]] = {}
    inventory_by_key: dict[tuple[int, int], Inventario] = {}
    branch_by_id = {branch.id_sucursal: branch for branch in branches}
    for product_index, product_spec in enumerate(spec.products):
        product = db.scalar(select(Producto).where(
            Producto.id_organizacion == organization.id_organizacion,
            Producto.nombre == product_spec.name,
        ))
        if product is None:
            product = Producto(
                id_organizacion=organization.id_organizacion,
                id_proveedor=supplier.id_proveedor, id_coleccion=collection.id_coleccion,
                id_categoria=categories[product_spec.category].id_categoria,
                nombre=product_spec.name, descripcion=product_spec.description,
                precio_base=product_spec.price, estado="ACTIVO",
            )
            db.add(product)
            db.flush([product])
            counts.products += 1
        elif (product.id_categoria != categories[product_spec.category].id_categoria
              or Decimal(product.precio_base) != product_spec.price):
            raise SeedPreflightError(f"El producto {spec.slug}/{product_spec.name} existe con otro precio o categoría.")
        products.append(product)
        asset_url = f"/api/assets/catalog/catalog-prenda-{product_index % 5 + 1}.png"
        resource = db.scalar(select(RecursoVirtual).where(
            RecursoVirtual.id_producto == product.id_producto,
            RecursoVirtual.url_archivo == asset_url,
        ))
        if resource is None:
            db.add(RecursoVirtual(
                id_producto=product.id_producto, tipo_recurso="imagen",
                url_archivo=asset_url, estado="ACTIVO",
            ))
        selected_sizes = ("S", "M", "L") if product_index % 2 == 0 else ("M", "L", "XL")
        color_start = (product_index + sum(ord(ch) for ch in spec.slug)) % len(COLOR_NAMES)
        selected_colors = (COLOR_NAMES[color_start], COLOR_NAMES[(color_start + 3) % len(COLOR_NAMES)])
        variants: list[ProductoVariante] = []
        for size_name in selected_sizes:
            for color_name in selected_colors:
                sku = f"{brand}-{product_index + 1:03d}-{_ascii(size_name).upper()}-{_ascii(color_name).replace('.', '')[:8].upper()}"
                variant = db.scalar(select(ProductoVariante).where(ProductoVariante.sku == sku))
                if variant is None:
                    variant = ProductoVariante(
                        id_producto=product.id_producto,
                        id_talla=sizes[size_name].id_talla,
                        id_color=colors[color_name].id_color,
                        sku=sku, estado="ACTIVO",
                    )
                    db.add(variant)
                    db.flush([variant])
                    counts.variants += 1
                elif variant.id_producto != product.id_producto:
                    raise SeedPreflightError(f"El SKU {sku} ya identifica otra variante.")
                variants.append(variant)
                variants_by_product.setdefault(product.id_producto, []).append(variant)
                for branch_index, branch in enumerate(branches):
                    inventory = db.scalar(select(Inventario).where(
                        Inventario.id_sucursal == branch.id_sucursal,
                        Inventario.id_variante == variant.id_variante,
                    ))
                    if inventory is None:
                        # One explicit zero-stock replacement option per tenant supports CU7.
                        zero_stock_case = product_index == 0 and size_name == selected_sizes[0] and color_name == selected_colors[0] and branch_index == 0
                        stock = 0 if zero_stock_case else 7 + ((product_index * 5 + branch_index * 3 + len(variants)) % 15)
                        inventory = Inventario(
                            id_sucursal=branch.id_sucursal, id_variante=variant.id_variante,
                            stock_disponible=stock, stock_reservado=0, stock_vendido=0,
                        )
                        db.add(inventory)
                        db.flush([inventory])
                        counts.inventories += 1
                        if stock:
                            _movement(
                                db, inventory, "ENTRADA", stock, 0, stock,
                                f"Carga inicial del catálogo {spec.slug} {sku}",
                                users["ADMINISTRADOR"].id_usuario,
                            )
                            counts.opening_movements += 1
                    inventory_by_key[(branch.id_sucursal, variant.id_variante)] = inventory
    return products, variants_by_product, inventory_by_key


def _movement(db: Session, inventory: Inventario, kind: str, quantity: int,
              before: int, after: int, reason: str, user_id: int) -> None:
    db.add(MovimientoInventario(
        id_inventario=inventory.id_inventario, tipo_movimiento=kind,
        cantidad=quantity, stock_anterior=before, stock_nuevo=after,
        motivo=reason[:255], id_usuario=user_id,
    ))


def _tenant_feature(db: Session, plan: Plan, code: str) -> bool:
    row = db.scalar(select(PlanCaracteristica).where(
        PlanCaracteristica.plan_id == plan.id_plan,
        PlanCaracteristica.codigo == code,
    ))
    return bool(row and row.habilitada)


def _seed_loyalty_program(
    db: Session, spec: TenantSpec, organization: Organizacion, plan: Plan,
    users: dict[str, object], counts: _Counts,
) -> bool:
    if spec.plan_code != "GLAMOUR" or not _tenant_feature(db, plan, "fidelizacion_clientes"):
        return False
    service = LoyaltyService(db, organization.id_organizacion)
    program = service.program()
    if program is None:
        service.configure({
            "active": True, "name": f"Club {spec.name}",
            "points_per_currency": Decimal("1.0000"),
            "currency_per_point": Decimal("0.0100"),
            "minimum_redeem_points": 100, "max_discount_percent": Decimal("20.00"),
            "expiration_days": 365,
        }, users["ADMINISTRADOR"])
        program = service.program()
        counts.loyalty_programs += 1
    elif not program.active:
        raise SeedPreflightError(f"El programa de fidelización existente de {spec.slug} está inactivo; no se cambia.")
    if program is None:
        raise RuntimeError("No se pudo preparar el programa de fidelización.")
    tiers = (
        ("BRONCE", "Bronce", 0), ("PLATA", "Plata", 500), ("ORO", "Oro", 1500),
    )
    for code, name, minimum in tiers:
        tier = db.scalar(select(LoyaltyTier).where(
            LoyaltyTier.organization_id == organization.id_organizacion,
            LoyaltyTier.code == code,
        ))
        if tier is None:
            db.add(LoyaltyTier(
                organization_id=organization.id_organizacion, code=code,
                name=name, minimum_points=minimum,
            ))
        elif tier.name != name or tier.minimum_points != minimum:
            raise SeedPreflightError(f"El nivel de fidelización {code} ya tiene otra configuración.")
    for user in users["CLIENTE"]:
        customer = db.scalar(select(Cliente).where(Cliente.id_usuario == user.id_usuario))
        account = db.scalar(select(LoyaltyAccount).where(
            LoyaltyAccount.organization_id == organization.id_organizacion,
            LoyaltyAccount.customer_id == customer.id_cliente,
        ))
        if account is None:
            db.add(LoyaltyAccount(
                organization_id=organization.id_organizacion, customer_id=customer.id_cliente,
                balance=0, earned_total=0, redeemed_total=0, expired_total=0,
            ))
            counts.loyalty_accounts += 1
    db.flush()
    return True


def _reservation_statuses(count: int) -> list[str]:
    completed = max(1, count // 9)
    cancelled = max(1, count // 5)
    expired = max(1, count // 10)
    remaining = count - completed - cancelled - expired
    pending = max(1, remaining // 2)
    confirmed = remaining - pending
    return (
        ["PENDIENTE"] * pending + ["CONFIRMADA"] * confirmed
        + ["CANCELADA"] * cancelled + ["VENCIDA"] * expired
        + ["COMPLETADA"] * completed
    )


def _seed_reservations(
    db: Session, spec: TenantSpec, organization: Organizacion,
    branches: list[Sucursal], users: dict[str, object], products: list[Producto],
    variants: dict[int, list[ProductoVariante]], inventories: dict[tuple[int, int], Inventario],
    counts: _Counts,
) -> list[_Sale]:
    statuses = _reservation_statuses(spec.reservation_count)
    completed_sales: list[_Sale] = []
    all_variants = [variant for product in products for variant in variants[product.id_producto]]
    customers = users["CLIENTE"]
    cashiers = users["CAJERO"]
    for index, target_state in enumerate(statuses):
        marker = f"SEED:{spec.slug}:RESERVATION:{index + 1:02d}"
        existing = db.scalar(select(Pedido).where(Pedido.referencia_entrega == marker))
        if existing is not None:
            if existing.estado == "ENTREGADO":
                completed_sales.append(_sale_from_order(db, existing))
            continue
        user = customers[(index * 7) % max(1, len(customers) - 4)]
        customer = user.cliente
        branch = branches[index % len(branches)]
        variant = all_variants[(index * 11 + 2) % len(all_variants)]
        inventory = inventories[(branch.id_sucursal, variant.id_variante)]
        quantity = 1 + (index % 2)
        if inventory.stock_disponible < quantity:
            candidates = [
                (candidate_branch, candidate_variant, inventories[(candidate_branch.id_sucursal, candidate_variant.id_variante)])
                for candidate_branch in branches for candidate_variant in all_variants
                if inventories[(candidate_branch.id_sucursal, candidate_variant.id_variante)].stock_disponible >= quantity
            ]
            if not candidates:
                raise SeedPreflightError(f"No hay stock inicial suficiente para reservar en {spec.slug}.")
            branch, variant, inventory = candidates[index % len(candidates)]
        price = Decimal(current_price(db, variant.producto)).quantize(Decimal("0.01"))
        stamp = _stamp(index % 18, index + 5)
        order = Pedido(
            id_cliente=customer.id_cliente, id_vendedor=cashiers[index % len(cashiers)].id_usuario,
            fecha_pedido=stamp, estado="PENDIENTE", total=(price * quantity).quantize(Decimal("0.01")),
            tipo_cliente="CLIENTE_REGISTRADO", tipo_venta="PRESENCIAL",
            tipo_entrega="RECOJO_SUCURSAL", id_sucursal_entrega=branch.id_sucursal,
            referencia_entrega=marker,
        )
        db.add(order)
        db.flush([order])
        reservation = Reserva(
            id_usuario=user.id_usuario, id_inventario=inventory.id_inventario,
            id_pedido=order.id_pedido, cantidad=quantity,
            estado="CONFIRMADA" if target_state == "COMPLETADA" else "PENDIENTE",
            fecha=stamp, fecha_expiracion=stamp + timedelta(days=2),
        )
        before = inventory.stock_disponible
        inventory.stock_disponible -= quantity
        inventory.stock_reservado += quantity
        db.add(reservation)
        db.flush([reservation])
        detail = PedidoDetalle(
            id_pedido=order.id_pedido, id_variante=variant.id_variante,
            id_reserva=reservation.id_reserva, cantidad=quantity, precio_unitario=price,
        )
        db.add(detail)
        _movement(db, inventory, "RESERVA", quantity, before, inventory.stock_disponible,
                  f"Reserva {marker}", user.id_usuario)
        if target_state in {"CANCELADA", "VENCIDA"}:
            previous = inventory.stock_disponible
            inventory.stock_disponible += quantity
            inventory.stock_reservado -= quantity
            reservation.estado = target_state
            order.estado = "CANCELADO"
            _movement(db, inventory, "LIBERACION_RESERVA", quantity, previous,
                      inventory.stock_disponible, f"Liberación {marker}", user.id_usuario)
        elif target_state == "COMPLETADA":
            db.flush([detail])
            payment = _create_simulated_payment(
                db, order, user, "QR", stamp,
                operation_key=f"{spec.slug}:reservation:{index + 1}",
            )
            order.fecha_entrega = stamp
            order.estado = "ENTREGADO"
            payment.fecha_pago = stamp
            completed_sales.append(_Sale(order, [detail], branch))
        counts.reservations += 1
        db.flush()
    return completed_sales


def _stamp(age_days: int, salt: int) -> datetime:
    local_day = datetime.now(timezone.utc).date() - timedelta(days=age_days)
    hour = 9 + (salt * 7) % 10
    minute = (salt * 23 + 11) % 60
    return datetime.combine(local_day, time(hour, minute), tzinfo=timezone.utc)


def _create_simulated_payment(
    db: Session, order: Pedido, user: Usuario, method: str, stamp: datetime,
    *, operation_key: str,
) -> Pago:
    from app.database.render_seed_safety import APPROVED_RENDER_POSTGRES_ID

    local_simulation = (
        settings.environment.lower() in {"development", "test"}
        and settings.payment_simulation_mode
    )
    verified_render_seed = (
        settings.environment.lower() == "production"
        and db.info.get("verified_render_postgres_id") == APPROVED_RENDER_POSTGRES_ID
    )
    if not (local_simulation or verified_render_seed):
        raise SeedPreflightError("No se permiten cobros de demostración fuera del modo local de simulación.")
    payment_service = PaymentService(db)
    key = uuid5(NAMESPACE_URL, f"fashionstore-seed-payment:{operation_key}")
    if method == "TARJETA":
        intent = SimulatedStripeCardPaymentProvider.create_intent(order.total, order.id_pedido)
        response = payment_service.create_stripe_payment(
            order.id_pedido, user.cliente.id_cliente, intent, simulated=True, commit=False,
        )
    else:
        response = payment_service.create_payment(
            CreatePaymentRequest(id_pedido=order.id_pedido, metodo_pago=method, operation_uuid=key),
            user.cliente.id_cliente, commit=False,
        )
        if method == "QR":
            demo = QRPaymentProvider.create_demo_request(order.id_pedido, order.total, settings.stripe_currency)
            payment_service.attach_demo_qr_reference(response.id_pago, demo["reference"], commit=False)
    approved = payment_service.approve_payment(
        response.id_pago, user.cliente.id_cliente, commit=False,
    )
    payment = db.get(Pago, approved.id_pago)
    payment.fecha_pago = stamp
    return payment


def _sale_from_order(db: Session, order: Pedido) -> _Sale:
    details = list(db.scalars(select(PedidoDetalle).where(
        PedidoDetalle.id_pedido == order.id_pedido
    ).order_by(PedidoDetalle.id_detalle)).all())
    branch = db.get(Sucursal, order.id_sucursal_entrega) if order.id_sucursal_entrega else None
    return _Sale(order, details, branch)


def _seed_paid_sales(
    db: Session, spec: TenantSpec, organization: Organizacion,
    branches: list[Sucursal], users: dict[str, object], products: list[Producto],
    variants: dict[int, list[ProductoVariante]], inventories: dict[tuple[int, int], Inventario],
    target: int, counts: _Counts,
) -> list[_Sale]:
    sales: list[_Sale] = []
    customers = users["CLIENTE"]
    cashiers = users["CAJERO"]
    all_variants = [variant for product in products for variant in variants[product.id_producto]]
    for index in range(target):
        marker = f"SEED:{spec.slug}:SALE:{index + 1:04d}"
        existing = db.scalar(select(Pedido).where(Pedido.referencia_entrega == marker))
        if existing is not None:
            sales.append(_sale_from_order(db, existing))
            continue
        age = index % 7 if index < max(20, spec.exchange_scenarios * 2) else 7 + (index * 17 % 84)
        stamp = _stamp(age, index + 31)
        cash_sale = index < max(20, spec.exchange_scenarios * 2) or index % 10 < 7
        branch = branches[index % len(branches)] if cash_sale else None
        customer_index = (index * 7 + index // 3) % max(1, len(customers) - 4)
        customer_user = customers[customer_index]
        customer = customer_user.cliente
        line_count = 1 + ((index * 3) % 3)
        chosen: list[tuple[ProductoVariante, int, Inventario | None]] = []
        start = (index * 13 + len(spec.slug)) % len(all_variants)
        attempts = 0
        cursor = start
        while len(chosen) < line_count and attempts < len(all_variants) * 2:
            variant = all_variants[cursor % len(all_variants)]
            inventory = inventories[(branch.id_sucursal, variant.id_variante)] if branch else None
            quantity = 1 + ((index + len(chosen)) % 2)
            if (all(item[0].id_variante != variant.id_variante for item in chosen)
                    and (inventory is None or inventory.stock_disponible >= quantity)):
                chosen.append((variant, quantity, inventory))
            cursor += 7
            attempts += 1
        if len(chosen) < 1:
            raise SeedPreflightError(f"No hay inventario para registrar ventas en {spec.slug}.")
        if cash_sale:
            payload_lines = [{"id_variante": variant.id_variante, "cantidad": quantity}
                             for variant, quantity, _ in chosen]
            estimate = sum(Decimal(current_price(db, variant.producto)) * quantity
                           for variant, quantity, _ in chosen)
            cashier = next(user for user in cashiers if user.id_sucursal == branch.id_sucursal)
            actor = SyncActor(
                user_id=cashier.id_usuario,
                organization_id=organization.id_organizacion, role="CAJERO",
            )
            result = create_offline_pos_sale(db, actor, {
                "id_sucursal": branch.id_sucursal,
                "id_cliente": customer.id_cliente,
                "lineas": payload_lines,
                "importe_recibido": str(estimate + Decimal(index % 12 + 1)),
            })
            db.flush()
            order = db.get(Pedido, result["id_pedido"])
            order.referencia_entrega = marker
            order.fecha_pedido = stamp
            order.fecha_entrega = stamp
            details = list(db.scalars(select(PedidoDetalle).where(
                PedidoDetalle.id_pedido == order.id_pedido
            ).order_by(PedidoDetalle.id_detalle)).all())
            payment = db.scalar(select(Pago).where(Pago.id_pedido == order.id_pedido))
            if payment is not None:
                payment.fecha_pago = stamp
            if order.id_cliente is not None:
                LoyaltyService(db, organization.id_organizacion).accrue_for_order(
                    order.id_pedido, order.id_vendedor,
                )
            sales.append(_Sale(order, details, branch))
        else:
            order = Pedido(
                id_cliente=customer.id_cliente, fecha_pedido=stamp,
                estado="PENDIENTE",
                total=sum((Decimal(current_price(db, variant.producto)) * quantity
                           for variant, quantity, _ in chosen), Decimal("0.00")).quantize(Decimal("0.01")),
                tipo_cliente="CLIENTE_REGISTRADO", tipo_venta="ONLINE",
                tipo_entrega="DELIVERY", direccion_entrega="Dirección sintética de entrega, Santa Cruz",
                referencia_entrega=marker, telefono_entrega=customer_user.telefono,
            )
            db.add(order)
            db.flush([order])
            details = []
            for variant, quantity, _ in chosen:
                detail = PedidoDetalle(
                    id_pedido=order.id_pedido, id_variante=variant.id_variante,
                    cantidad=quantity, precio_unitario=Decimal(current_price(db, variant.producto)),
                )
                db.add(detail)
                details.append(detail)
            db.flush(details)
            method = "QR" if index % 10 in (7, 8) else "TARJETA"
            payment = _create_simulated_payment(
                db, order, customer_user, method, stamp,
                operation_key=f"{spec.slug}:sale:{index + 1}",
            )
            order.fecha_pedido = stamp
            sales.append(_Sale(order, details, None))
        counts.paid_sales += 1
        db.flush()
    return sales


def _seed_cancelled_scenarios(
    db: Session, spec: TenantSpec, organization: Organizacion, branches: list[Sucursal],
    users: dict[str, object], products: list[Producto],
    variants: dict[int, list[ProductoVariante]], counts: _Counts,
) -> None:
    for index in range(4):
        marker = f"SEED:{spec.slug}:CANCELLED:{index + 1:02d}"
        if db.scalar(select(Pedido.id_pedido).where(Pedido.referencia_entrega == marker)) is not None:
            continue
        customer_user = users["CLIENTE"][(index * 9 + 2) % len(users["CLIENTE"])]
        product = products[(index * 5 + 1) % len(products)]
        variant = variants[product.id_producto][index % len(variants[product.id_producto])]
        price = Decimal(current_price(db, product))
        order = Pedido(
            id_cliente=customer_user.cliente.id_cliente,
            id_vendedor=users["CAJERO"][index % len(users["CAJERO"])].id_usuario,
            fecha_pedido=_stamp(15 + index * 12, 201 + index),
            estado="CANCELADO", total=price, tipo_cliente="CLIENTE_REGISTRADO",
            tipo_venta="PRESENCIAL", tipo_entrega="RECOJO_SUCURSAL",
            id_sucursal_entrega=branches[index % len(branches)].id_sucursal,
            referencia_entrega=marker,
        )
        db.add(order)
        db.flush([order])
        db.add(PedidoDetalle(
            id_pedido=order.id_pedido, id_variante=variant.id_variante,
            cantidad=1, precio_unitario=price,
        ))
        db.add(Pago(
            id_pedido=order.id_pedido, metodo_pago="QR", monto=price,
            estado="FALLIDO", proveedor="STRIPE_SIMULADO", simulated=True,
        ))
        counts.cancelled_orders += 1


def _seed_exchanges(
    db: Session, spec: TenantSpec, organization: Organizacion,
    branches: list[Sucursal], sales: list[_Sale],
    variants: dict[int, list[ProductoVariante]],
    inventories: dict[tuple[int, int], Inventario], counts: _Counts,
) -> None:
    replaceable_categories = {
        product.id_categoria
        for product in db.scalars(select(Producto).where(
            Producto.id_organizacion == organization.id_organizacion,
        )).all()
        if db.scalar(select(func.count()).select_from(Producto).where(
            Producto.id_organizacion == organization.id_organizacion,
            Producto.id_categoria == product.id_categoria,
        )) > 1
    }
    candidates = [sale for sale in sales if sale.branch is not None
                  and sale.order.estado == "ENTREGADO" and sale.order.id_cliente is not None
                  and sale.order.fecha_entrega is not None and sale.details
                  and sale.details[0].variante.producto.id_categoria in replaceable_categories]
    candidates = [sale for sale in candidates if (
        datetime.now(timezone.utc).date() - _as_utc(sale.order.fecha_entrega).date()
    ).days <= 7]
    if len(candidates) < spec.exchange_scenarios:
        raise SeedPreflightError(f"No hay compras elegibles recientes para los cambios de {spec.slug}.")
    for index, sale in enumerate(candidates[:spec.exchange_scenarios]):
        detail = sale.details[0]
        original = detail.variante
        options = [variant for product in variants.values() for variant in product
                   if variant.producto.id_categoria == original.producto.id_categoria
                   and variant.id_producto != original.id_producto]
        if not options:
            raise SeedPreflightError(f"Falta una variante sustituta de la categoría {original.producto.categoria.nombre}.")
        branch_id = sale.branch.id_sucursal
        no_stock_options = [variant for variant in options
                            if inventories[(branch_id, variant.id_variante)].stock_disponible == 0]
        replacement = no_stock_options[0] if index == spec.exchange_scenarios - 1 and no_stock_options else options[index % len(options)]
        marker = str(uuid5(NAMESPACE_URL, f"fashionstore-seed-exchange:{spec.slug}:{index + 1}"))
        if db.scalar(select(func.count()).select_from(GarmentExchange).where(
            GarmentExchange.organization_id == organization.id_organizacion,
            GarmentExchange.operation_uuid == marker,
        )):
            continue
        customer_user = db.scalar(select(Usuario).join(Cliente).where(
            Cliente.id_cliente == sale.order.id_cliente,
        ))
        create_customer_request(
            db, organization_id=organization.id_organizacion,
            customer_user_id=customer_user.id_usuario,
            detail_id=detail.id_detalle, branch_id=branch_id,
            replacement_variant_id=replacement.id_variante,
            reason=("Cambio de talla solicitado dentro del plazo" if index % 2 == 0
                    else "Cambio de color por preferencia del cliente"),
            operation_uuid=marker,
        )
        counts.exchange_scenarios += 1


def _seed_loyalty_adjustments(
    db: Session, spec: TenantSpec, organization: Organizacion,
    users: dict[str, object], sales: list[_Sale],
    inventories: dict[tuple[int, int], Inventario], counts: _Counts,
) -> None:
    service = LoyaltyService(db, organization.id_organizacion)
    eligible = [sale for sale in sales if sale.order.id_cliente is not None
                and sale.order.estado in {"ENTREGADO", "CONFIRMADO"}]
    if not eligible:
        return
    # Use actual paid sales as the source for a point redemption.
    by_customer: dict[int, list[_Sale]] = {}
    for sale in eligible:
        by_customer.setdefault(sale.order.id_cliente, []).append(sale)
    account_rows = list(db.scalars(select(LoyaltyAccount).where(
        LoyaltyAccount.organization_id == organization.id_organizacion
    ).order_by(LoyaltyAccount.balance.desc())).all())
    redemption_sale = next((sale for account in account_rows if account.balance >= 100
                            for sale in by_customer.get(account.customer_id, [])), None)
    if redemption_sale is not None:
        redemption_key = f"redeem:order:{redemption_sale.order.id_pedido}"
        exists = db.scalar(select(LoyaltyLedger.id).where(
            LoyaltyLedger.organization_id == organization.id_organizacion,
            LoyaltyLedger.event_key == redemption_key,
        ))
        if exists is None:
            customer = redemption_sale.order.cliente
            result = service.redeem_for_order(
                customer.id_cliente, redemption_sale.order, 100,
                actor_id=users["ADMINISTRADOR"].id_usuario,
            )
            payment = db.scalar(select(Pago).where(Pago.id_pedido == redemption_sale.order.id_pedido))
            if payment is not None:
                payment.monto = redemption_sale.order.total
            if result["points"]:
                counts.loyalty_movements += 1
    return_sale = next((sale for sale in eligible if sale.branch is not None
                        and sale.details and sale.details[0].cantidad > 0), None)
    if return_sale is None:
        return
    detail = return_sale.details[0]
    already_returned = db.scalar(select(Devolucion.id_devolucion).where(
        Devolucion.id_detalle == detail.id_detalle,
    ))
    if already_returned is not None:
        return
    inventory = inventories[(return_sale.branch.id_sucursal, detail.id_variante)]
    stamp = _as_utc(return_sale.order.fecha_entrega or return_sale.order.fecha_pedido)
    returned = Devolucion(
        id_detalle=detail.id_detalle, id_inventario=inventory.id_inventario,
        id_usuario=users["ADMINISTRADOR"].id_usuario, cantidad=1,
        motivo="Devolución de muestra vinculada a compra pagada", estado="COMPLETADA",
        fecha=stamp + timedelta(days=1),
    )
    db.add(returned)
    db.flush([returned])
    previous = inventory.stock_disponible
    inventory.stock_disponible += 1
    _movement(
        db, inventory, "ENTRADA", 1, previous, inventory.stock_disponible,
        f"Devolución de muestra pedido {return_sale.order.id_pedido}",
        users["ADMINISTRADOR"].id_usuario,
    )
    reversed_points = service.reverse_for_return(
        returned.id_devolucion, users["ADMINISTRADOR"].id_usuario,
    )
    counts.loyalty_movements += int(reversed_points > 0)


def _assert_tenant_invariants(
    db: Session, spec: TenantSpec, organization: Organizacion,
    branches: list[Sucursal], variants: dict[int, list[ProductoVariante]],
    inventories: dict[tuple[int, int], Inventario], sales: list[_Sale],
) -> None:
    if organization.slug != spec.slug or organization.nombre != spec.name:
        raise SeedPreflightError(f"Aislamiento inválido para {spec.slug}.")
    if len(branches) != len(spec.branches):
        raise SeedPreflightError(f"Cantidad de sucursales incorrecta para {spec.slug}.")
    for branch, branch_spec in zip(branches, spec.branches):
        if branch.id_organizacion != organization.id_organizacion:
            raise SeedPreflightError(f"Sucursal de otro tenant detectada en {spec.slug}.")
        if branch.estado.upper() != ("ACTIVA" if branch_spec.active else "INACTIVA"):
            raise SeedPreflightError(f"Estado de sucursal inesperado en {spec.slug}/{branch.nombre}.")
    for product_variants in variants.values():
        if not 3 <= len(product_variants) <= 8:
            raise SeedPreflightError(f"Cantidad de variantes inesperada para {spec.slug}.")
        for variant in product_variants:
            if variant.producto.id_organizacion != organization.id_organizacion:
                raise SeedPreflightError(f"Variante compartida entre organizaciones en {spec.slug}.")
            for branch in branches:
                inventory = inventories[(branch.id_sucursal, variant.id_variante)]
                if min(inventory.stock_disponible, inventory.stock_reservado, inventory.stock_vendido) < 0:
                    raise SeedPreflightError(f"Stock negativo en {spec.slug}/{branch.nombre}.")
    for sale in sales:
        if sale.order.id_cliente is not None:
            customer_org = sale.order.cliente.usuario.id_organizacion
            if customer_org != organization.id_organizacion:
                raise SeedPreflightError(f"Venta de otro tenant detectada en {spec.slug}.")
        if sale.order.estado in {"ENTREGADO", "CONFIRMADO"}:
            payment = db.scalar(select(Pago).where(
                Pago.id_pedido == sale.order.id_pedido, Pago.estado == "PAGADO",
            ))
            if payment is None or Decimal(payment.monto) != Decimal(sale.order.total):
                raise SeedPreflightError(f"Venta pagada sin pago consistente en {spec.slug}.")


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
