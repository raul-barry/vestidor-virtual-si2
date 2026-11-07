"""Idempotent local SaaS demonstration data seed. Requires DEMO_SEED_PASSWORD."""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.core.config import settings
from app.core.security import hash_password
from app.database.database import SessionLocal
from app.database.plan_seed import seed_commercial_plans
from app.database.seed import seed_roles
from app.models.carrito import Carrito
from app.models.carrito_detalle import CarritoDetalle
from app.models.categoria import Categoria
from app.models.cliente import Cliente
from app.models.color import Color
from app.models.exchange import GarmentExchange
from app.models.inventario import Inventario
from app.models.organizacion import Organizacion
from app.models.pago import Pago
from app.models.pedido import Pedido
from app.models.pedido_detalle import PedidoDetalle
from app.models.producto import Producto
from app.models.producto_variante import ProductoVariante
from app.models.recurso_virtual import RecursoVirtual
from app.models.reserva import Reserva
from app.models.rol import Rol
from app.models.sucursal import Sucursal
from app.models.suscripcion import Suscripcion
from app.models.talla import Talla
from app.models.usuario import Usuario
from app.services.payment_providers import QRPaymentProvider
from app.services.payment_service import PaymentService
from app.schemas.payment import CreatePaymentRequest
from app.services.stock_sale_service import hold_order_stock


ORGANIZATIONS = (
    ("FashionStore", "fashionstore", "ESTILO", 2),
    ("UrbanVogue", "urbanvogue", "MODA", 3),
    ("Elegance Boutique", "elegance-boutique", "GLAMOUR", 3),
)
ROLE_COUNTS = (
    ("ADMINISTRADOR", 1), ("ENCARGADO_SUCURSAL", 2), ("CAJERO", 2),
    ("EMPLEADO", 3), ("CLIENTE", 10),
)
SIZES = ("S", "M", "L")
COLORS = ("Negro", "Blanco", "Azul")
CATEGORIES = ("Camisas", "Pantalones", "Chaquetas", "Vestidos", "Accesorios")
PRODUCT_COUNT = 15
BRANCH_TARGETS = {"fashionstore": 2, "urbanvogue": 3, "elegance-boutique": 3}


def _named(db: Session, model, name: str, **values):
    row = db.scalar(select(model).where(model.nombre == name))
    if row is not None:
        return row, False
    row = model(nombre=name, **values)
    db.add(row)
    db.flush()
    return row, True


def _organization(db: Session, name: str, slug: str) -> tuple[Organizacion, bool]:
    row = db.scalar(select(Organizacion).where(Organizacion.slug == slug))
    if row is not None:
        return row, False
    row = Organizacion(nombre=name, slug=slug, estado="ACTIVA")
    db.add(row)
    db.flush()
    return row, True


def _branches(db: Session, organization: Organizacion, target_count: int) -> tuple[list[Sucursal], int]:
    rows = list(db.scalars(select(Sucursal).where(
        Sucursal.id_organizacion == organization.id_organizacion
    ).order_by(Sucursal.id_sucursal)).all())
    if len([row for row in rows if row.estado.upper() == "ACTIVA"]) > target_count:
        raise ValueError(f"{organization.slug} already exceeds its demonstration plan branch limit")
    created = 0
    number = 1
    while len([row for row in rows if row.estado.upper() == "ACTIVA"]) < target_count:
        name = f"Demo Sucursal {number:02d}"
        number += 1
        if any(row.nombre == name for row in rows):
            continue
        row = Sucursal(
            id_organizacion=organization.id_organizacion,
            nombre=name,
            direccion=f"Av. Demostración {100 + number}",
            ciudad="Santa Cruz",
            estado="ACTIVA",
        )
        db.add(row)
        db.flush()
        rows.append(row)
        created += 1
    return rows, created


def _subscription(db: Session, organization: Organizacion, plan_code: str) -> int:
    from app.models.plan import Plan

    plan = db.scalar(select(Plan).where(Plan.codigo == plan_code))
    current = db.scalar(select(Suscripcion).where(
        Suscripcion.organizacion_id == organization.id_organizacion,
        Suscripcion.estado == "ACTIVA",
    ))
    if current is not None:
        if current.plan_id != plan.id_plan:
            raise ValueError(f"{organization.slug} already has a different active plan; seed will not replace it")
        return 0
    db.add(Suscripcion(
        organizacion_id=organization.id_organizacion,
        plan_id=plan.id_plan,
        estado="ACTIVA",
        fecha_inicio=datetime.now(timezone.utc) - timedelta(days=30),
    ))
    db.flush()
    return 1


def _users(db: Session, organization: Organizacion, branches: list[Sucursal], password_hash: str) -> tuple[dict[str, list[Usuario]], int]:
    roles = {row.nombre: row for row in db.scalars(select(Rol)).all()}
    users: dict[str, list[Usuario]] = {name: [] for name, _ in ROLE_COUNTS}
    created = 0
    for role_name, count in ROLE_COUNTS:
        for index in range(1, count + 1):
            email = f"{organization.slug}.{role_name.lower()}.{index:02d}@demo.test"
            user = db.scalar(select(Usuario).where(Usuario.correo == email))
            branch = None if role_name == "ADMINISTRADOR" else branches[(index - 1) % len(branches)]
            if user is None:
                user = Usuario(
                    id_organizacion=organization.id_organizacion,
                    id_sucursal=branch.id_sucursal if branch else None,
                    id_rol=roles[role_name].id_rol,
                    nombres=f"Demo {role_name.title().replace('_', ' ')} {index:02d}",
                    apellidos=organization.slug.replace("-", " ").title(),
                    correo=email,
                    password_hash=password_hash,
                    estado="ACTIVO",
                )
                db.add(user)
                db.flush()
                created += 1
            elif user.id_organizacion != organization.id_organizacion or user.id_rol != roles[role_name].id_rol:
                raise ValueError(f"Existing account {email} does not match this seed tenant and role")
            users[role_name].append(user)
            if role_name == "CLIENTE" and user.cliente is None:
                client = Cliente(id_usuario=user.id_usuario, estado="ACTIVO")
                user.cliente = client
                db.add(client)
                db.flush()
    return users, created


def _catalog(db: Session, organization: Organizacion, branches: list[Sucursal]) -> tuple[list[Producto], dict[tuple[int, int, int, int], tuple[ProductoVariante, Inventario]], dict[str, int]]:
    counts = {"categories": 0, "sizes": 0, "colors": 0, "products": 0, "variants": 0, "inventory": 0, "images": 0}
    categories = {}
    for name in CATEGORIES:
        row, added = _named(db, Categoria, name, descripcion=f"Categoría de demostración: {name}.")
        categories[name] = row
        counts["categories"] += int(added)
    sizes = {}
    for name in SIZES:
        sizes[name], added = _named(db, Talla, name)
        counts["sizes"] += int(added)
    colors = {}
    for name in COLORS:
        colors[name], added = _named(db, Color, name)
        counts["colors"] += int(added)

    products = []
    variants: dict[tuple[int, int, int, int], tuple[ProductoVariante, Inventario]] = {}
    for product_index in range(1, PRODUCT_COUNT + 1):
        product_name = f"{organization.nombre} Demo Prenda {product_index:02d}"
        product = db.scalar(select(Producto).where(
            Producto.id_organizacion == organization.id_organizacion,
            Producto.nombre == product_name,
        ))
        if product is None:
            product = Producto(
                id_organizacion=organization.id_organizacion,
                id_categoria=categories[CATEGORIES[(product_index - 1) % len(CATEGORIES)]].id_categoria,
                nombre=product_name,
                descripcion=f"Prenda sintética de demostración {product_index:02d} para {organization.nombre}.",
                precio_base=Decimal("89.90") + Decimal(product_index * 7),
                estado="ACTIVO",
            )
            db.add(product)
            db.flush()
            counts["products"] += 1
        products.append(product)
        image_url = f"/api/assets/catalog/catalog-prenda-{(product_index - 1) % 5 + 1}.png"
        if db.scalar(select(RecursoVirtual.id).where(
            RecursoVirtual.id_producto == product.id_producto,
            RecursoVirtual.url_archivo == image_url,
        )) is None:
            db.add(RecursoVirtual(id_producto=product.id_producto, tipo_recurso="imagen", url_archivo=image_url, estado="ACTIVO"))
            counts["images"] += 1

        for size_index, size_name in enumerate(SIZES):
            for color_index, color_name in enumerate(COLORS):
                sku = f"DEMO-{organization.slug.upper()}-{product_index:02d}-{size_name}-{color_name[:3].upper()}"
                variant = db.scalar(select(ProductoVariante).where(ProductoVariante.sku == sku))
                if variant is None:
                    variant = ProductoVariante(
                        id_producto=product.id_producto,
                        id_talla=sizes[size_name].id_talla,
                        id_color=colors[color_name].id_color,
                        sku=sku,
                        estado="ACTIVO",
                    )
                    db.add(variant)
                    db.flush()
                    counts["variants"] += 1
                for branch_index, branch in enumerate(branches):
                    inventory = db.scalar(select(Inventario).where(
                        Inventario.id_sucursal == branch.id_sucursal,
                        Inventario.id_variante == variant.id_variante,
                    ))
                    if inventory is None:
                        inventory = Inventario(
                            id_sucursal=branch.id_sucursal,
                            id_variante=variant.id_variante,
                            stock_disponible=30 + branch_index,
                            stock_reservado=0,
                            stock_vendido=0,
                        )
                        db.add(inventory)
                        db.flush()
                        counts["inventory"] += 1
                    variants[(product_index - 1, size_index, color_index, branch_index)] = (variant, inventory)
    return products, variants, counts


def _carts_and_reservations(db: Session, users: dict[str, list[Usuario]], branches: list[Sucursal], variants) -> tuple[int, int]:
    carts_created = reservations_created = 0
    clients = users["CLIENTE"]
    for index, user in enumerate(clients[:3]):
        client = db.scalar(select(Cliente).where(Cliente.id_usuario == user.id_usuario))
        cart = db.scalar(select(Carrito).where(Carrito.id_cliente == client.id_cliente))
        if cart is None:
            cart = Carrito(id_cliente=client.id_cliente, estado="ACTIVO")
            db.add(cart)
            db.flush()
            carts_created += 1
        variant, _inventory = variants[(index, 0, 0, index % len(branches))]
        if db.scalar(select(CarritoDetalle.id_detalle).where(
            CarritoDetalle.id_carrito == cart.id_carrito,
            CarritoDetalle.id_variante == variant.id_variante,
        )) is None:
            db.add(CarritoDetalle(
                id_carrito=cart.id_carrito,
                id_variante=variant.id_variante,
                cantidad=1,
                precio_unitario=variant.producto.precio_base,
            ))
            db.flush()
    for index, user in enumerate(clients[3:5]):
        variant, inventory = variants[(12 + index, 1, 1, index % len(branches))]
        exists = db.scalar(select(Reserva.id_reserva).where(
            Reserva.id_usuario == user.id_usuario,
            Reserva.id_inventario == inventory.id_inventario,
            Reserva.estado == "PENDIENTE",
        ))
        if exists:
            continue
        if inventory.stock_disponible < 1:
            raise ValueError("Not enough inventory to seed a demonstration reservation")
        inventory.stock_disponible -= 1
        inventory.stock_reservado += 1
        db.add(Reserva(
            id_usuario=user.id_usuario,
            id_inventario=inventory.id_inventario,
            cantidad=1,
            estado="PENDIENTE",
            fecha=datetime.now(timezone.utc),
            fecha_expiracion=datetime.now(timezone.utc) + timedelta(days=7),
        ))
        db.flush()
        reservations_created += 1
    return carts_created, reservations_created


def _historical_sales(db: Session, organization: Organizacion, branches: list[Sucursal], users, products, variants) -> int:
    if settings.environment not in ("development", "test") or not settings.payment_simulation_mode:
        raise RuntimeError("Historical demo sales require the existing local payment simulation mode")
    from app.models.pedido import Pedido

    created = 0
    db.info["skip_business_audit"] = True
    for branch_index, branch in enumerate(branches):
        for product_offset in range(3):
            product_index = branch_index * 3 + product_offset
            product = products[product_index]
            variant, _inventory = variants[(product_index, 1, 2, branch_index)]
            for week in range(6):
                marker = f"DEMO-SEED:{organization.slug}:SALE:{branch_index + 1}:{product_index + 1}:{week + 1}"
                order = db.scalar(select(Pedido).where(Pedido.referencia_entrega == marker))
                if order is None:
                    customer = users["CLIENTE"][(branch_index * 3 + product_offset + week) % 10]
                    vendor = users["CAJERO"][(branch_index + product_offset) % 2]
                    stamp = datetime.combine(date.today() - timedelta(days=14 * (week + 1)), datetime.min.time(), tzinfo=timezone.utc)
                    order = Pedido(
                        id_cliente=db.scalar(select(Cliente.id_cliente).where(Cliente.id_usuario == customer.id_usuario)),
                        id_vendedor=vendor.id_usuario,
                        fecha_pedido=stamp,
                        estado="PENDIENTE",
                        total=product.precio_base,
                        tipo_cliente="CLIENTE_REGISTRADO",
                        tipo_venta="PRESENCIAL",
                        tipo_entrega="RETIRO_SUCURSAL",
                        id_sucursal_entrega=branch.id_sucursal,
                        referencia_entrega=marker,
                    )
                    db.add(order)
                    db.flush()
                    db.add(PedidoDetalle(
                        id_pedido=order.id_pedido,
                        id_variante=variant.id_variante,
                        cantidad=1,
                        precio_unitario=product.precio_base,
                    ))
                    db.flush()
                payment = db.scalar(select(Pago).where(Pago.id_pedido == order.id_pedido))
                if payment is not None and payment.estado == "PAGADO":
                    continue
                hold_order_stock(db, order)
                operation_uuid = uuid5(NAMESPACE_URL, marker)
                service = PaymentService(db)
                payment_response = service.create_payment(
                    CreatePaymentRequest(id_pedido=order.id_pedido, metodo_pago="QR", operation_uuid=operation_uuid)
                )
                payment = service.repository.get_payment_by_id(payment_response.id_pago)
                if payment.referencia_externa is None:
                    demo_request = QRPaymentProvider.create_demo_request(order.id_pedido, order.total, settings.stripe_currency)
                    service.attach_demo_qr_reference(payment.id_pago, demo_request["reference"])
                service.approve_payment(payment.id_pago)
                created += 1
    return created


def _exchange(db: Session, organization: Organizacion, branches: list[Sucursal], users, products, variants) -> int:
    marker = uuid5(NAMESPACE_URL, f"DEMO-SEED:{organization.slug}:EXCHANGE:1")
    existing = db.scalar(select(GarmentExchange).where(
        GarmentExchange.organization_id == organization.id_organizacion,
        GarmentExchange.operation_uuid == str(marker),
    ))
    if existing is not None:
        return 0
    order = db.scalar(select(Pedido).where(Pedido.referencia_entrega.like(f"DEMO-SEED:{organization.slug}:SALE:%")).order_by(Pedido.fecha_pedido.desc()))
    if order is None or not order.detalles:
        return 0
    detail = order.detalles[0]
    original = detail.variante
    replacement, replacement_inventory = variants[(1, 2, 1, 0)]
    original_inventory = db.scalar(select(Inventario).join(Sucursal).where(
        Inventario.id_variante == original.id_variante,
        Sucursal.id_organizacion == organization.id_organizacion,
        Sucursal.id_sucursal == order.id_sucursal_entrega,
    ))
    db.add(GarmentExchange(
        organization_id=organization.id_organizacion,
        operation_uuid=str(marker),
        customer_id=order.id_cliente,
        original_order_id=order.id_pedido,
        original_detail_id=detail.id_detalle,
        original_variant_id=original.id_variante,
        replacement_variant_id=replacement.id_variante,
        branch_id=order.id_sucursal_entrega,
        replacement_branch_id=branches[0].id_sucursal,
        original_inventory_id=original_inventory.id_inventario if original_inventory else None,
        replacement_inventory_id=replacement_inventory.id_inventario,
        employee_id=users["EMPLEADO"][0].id_usuario,
        quantity=1,
        purchase_date=order.fecha_pedido,
        delivery_date=order.fecha_pedido + timedelta(days=1),
        requested_at=datetime.now(timezone.utc),
        reason="Prueba de demostración de cambio de talla",
        inspection_state="PENDIENTE",
        state="SOLICITADO",
        original_paid_amount=detail.precio_unitario,
        replacement_amount=replacement.producto.precio_base,
        economic_difference=replacement.producto.precio_base - detail.precio_unitario,
        financial_state="PENDIENTE_AJUSTE" if replacement.producto.precio_base != detail.precio_unitario else "SIN_DIFERENCIA",
    ))
    db.flush()
    return 1


def seed_demo_data(db: Session, demo_password: str) -> dict:
    if settings.environment not in ("development", "test"):
        raise RuntimeError("Demonstration data can only be seeded in development or test environments")
    if not settings.database_url.startswith(("postgresql", "sqlite")):
        raise RuntimeError("Unsupported database target for demonstration seed")
    if len(demo_password) < 12:
        raise ValueError("DEMO_SEED_PASSWORD must contain at least 12 characters")

    db.info.pop("organization_id", None)
    db.info["skip_business_audit"] = True
    seed_roles(db)
    seed_commercial_plans(db)
    created = {"organizations": 0, "branches": 0, "subscriptions": 0, "users": 0,
               "products": 0, "variants": 0, "inventory": 0, "carts": 0,
               "reservations": 0, "demo_sales": 0, "exchanges": 0}
    password_hash = hash_password(demo_password)
    roles = {row.nombre for row in db.scalars(select(Rol)).all()}
    missing_roles = {name for name, _ in ROLE_COUNTS} - roles
    if missing_roles:
        raise RuntimeError(f"Missing required roles: {sorted(missing_roles)}")

    for name, slug, plan_code, branch_limit in ORGANIZATIONS:
        organization, was_created = _organization(db, name, slug)
        created["organizations"] += int(was_created)
        db.info["organization_id"] = organization.id_organizacion
        branches, added_branches = _branches(db, organization, BRANCH_TARGETS[slug])
        if len([row for row in branches if row.estado.upper() == "ACTIVA"]) > branch_limit:
            raise ValueError(f"{slug} exceeds the {plan_code} branch limit")
        created["branches"] += added_branches
        created["subscriptions"] += _subscription(db, organization, plan_code)
        users, added_users = _users(db, organization, branches, password_hash)
        created["users"] += added_users
        products, variants, counts = _catalog(db, organization, branches)
        created["products"] += counts["products"]
        created["variants"] += counts["variants"]
        created["inventory"] += counts["inventory"]
        cart_count, reservation_count = _carts_and_reservations(db, users, branches, variants)
        created["carts"] += cart_count
        created["reservations"] += reservation_count
        db.flush()
        created["demo_sales"] += _historical_sales(db, organization, branches, users, products, variants)
        created["exchanges"] += _exchange(db, organization, branches, users, products, variants)
        db.flush()
    db.info.pop("organization_id", None)
    db.info.pop("skip_business_audit", None)
    return created


def main() -> None:
    password = os.getenv("DEMO_SEED_PASSWORD")
    if not password:
        raise SystemExit("Set DEMO_SEED_PASSWORD securely before running the demonstration seed")
    db = SessionLocal()
    try:
        counts = seed_demo_data(db, password)
        db.commit()
        print(f"Demonstration seed completed: {counts}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
