from collections.abc import Iterable
from decimal import Decimal
from datetime import date, timedelta
from app.models.comercio import Ciudad, Proveedor, Coleccion, Promocion

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

import app.models  # noqa: F401  # Ensure all relationships are registered before seeding.
from app.core.security import hash_password
from app.database.database import SessionLocal
from app.models.categoria import Categoria
from app.models.cliente import Cliente
from app.models.color import Color
from app.models.inventario import Inventario
from app.models.recurso_virtual import RecursoVirtual
from app.models.producto import Producto
from app.models.producto_variante import ProductoVariante
from app.models.rol import Rol
from app.models.sucursal import Sucursal
from app.models.talla import Talla
from app.models.usuario import Usuario

INITIAL_ROLES = ("ADMINISTRADOR", "CLIENTE", "ENCARGADO_SUCURSAL", "CAJERO")
INITIAL_PASSWORDS = {
    "admin@vestidor.local": "Admin123!",
    "cliente@vestidor.local": "Cliente123!",
    "encargado@vestidor.local": "Encargado123!",
    "cajero@vestidor.local": "Cajero123!",
}
INITIAL_CATEGORIES = (
    ("Camisas", "Camisas masculinas para uso casual y formal."),
    ("Pantalones", "Pantalones masculinos para vestir y uso diario."),
    ("Chaquetas", "Chaquetas masculinas para temporada fresca."),
)
INITIAL_SIZES = ("M", "L", "XL")
INITIAL_COLORS = ("Azul", "Negro", "Blanco", "Gris", "Verde")
INITIAL_BRANCH = ("Sucursal Central", "Av. Principal 100")
INITIAL_PRODUCTS = (
    ("Camisa Oxford Azul", "Camisa manga larga de algodon para vestir.", "Camisas", Decimal("189.90"), "Azul"),
    ("Camisa Casual Blanca", "Camisa ligera para uso diario.", "Camisas", Decimal("159.90"), "Blanco"),
    ("Pantalon Chino Negro", "Pantalon chino de corte recto.", "Pantalones", Decimal("229.90"), "Negro"),
    ("Pantalon Jean Gris", "Jean masculino clasico de mezclilla.", "Pantalones", Decimal("249.90"), "Gris"),
    ("Chaqueta Bomber Verde", "Chaqueta bomber liviana con cierre frontal.", "Chaquetas", Decimal("319.90"), "Verde"),
)


def seed_roles(db: Session, role_names: Iterable[str] = INITIAL_ROLES) -> int:
    """Insert missing system roles and return the number of created records."""
    names = tuple(role_names)
    existing_names = set(db.scalars(select(Rol.nombre).where(Rol.nombre.in_(names))).all())
    roles_to_create = [Rol(nombre=name) for name in names if name not in existing_names]

    if roles_to_create:
        db.add_all(roles_to_create)
        db.flush()

    return len(roles_to_create)


def _get_or_create_named(db: Session, model, nombre: str, **values) -> tuple[object, bool]:
    record = db.scalar(select(model).where(model.nombre == nombre))
    if record is not None:
        return record, False

    record = model(nombre=nombre, **values)
    db.add(record)
    db.flush()
    return record, True


def _seed_users(db: Session) -> int:
    roles = {role.nombre: role for role in db.scalars(select(Rol)).all()}
    created = 0

    admin = db.scalar(select(Usuario).where(Usuario.correo == "admin@vestidor.local"))
    if admin is None:
        db.add(
            Usuario(
                id_rol=roles["ADMINISTRADOR"].id_rol,
                nombres="Administrador",
                apellidos="Vestidor",
                correo="admin@vestidor.local",
                telefono=None,
                password_hash=hash_password(INITIAL_PASSWORDS["admin@vestidor.local"]),
                estado="ACTIVO",
            )
        )
        created += 1

    client = db.scalar(select(Usuario).where(Usuario.correo == "cliente@vestidor.local"))
    if client is None:
        client = Usuario(
            id_rol=roles["CLIENTE"].id_rol,
            nombres="Cliente",
            apellidos="Prueba",
            correo="cliente@vestidor.local",
            telefono=None,
            password_hash=hash_password(INITIAL_PASSWORDS["cliente@vestidor.local"]),
            estado="ACTIVO",
        )
        db.add(client)
        db.flush()
        db.add(Cliente(id_usuario=client.id_usuario, estado="ACTIVO"))
        created += 1
    elif client.cliente is None:
        db.add(Cliente(id_usuario=client.id_usuario, estado="ACTIVO"))

    encargado = db.scalar(select(Usuario).where(Usuario.correo == "encargado@vestidor.local"))
    if encargado is None and "ENCARGADO_SUCURSAL" in roles:
        db.add(
            Usuario(
                id_rol=roles["ENCARGADO_SUCURSAL"].id_rol,
                nombres="Encargado",
                apellidos="Sucursal",
                correo="encargado@vestidor.local",
                telefono=None,
                password_hash=hash_password(INITIAL_PASSWORDS["encargado@vestidor.local"]),
                estado="ACTIVO",
            )
        )
        created += 1

    cajero = db.scalar(select(Usuario).where(Usuario.correo == "cajero@vestidor.local"))
    if cajero is None and "CAJERO" in roles:
        db.add(
            Usuario(
                id_rol=roles["CAJERO"].id_rol,
                nombres="Cajero",
                apellidos="Principal",
                correo="cajero@vestidor.local",
                telefono=None,
                password_hash=hash_password(INITIAL_PASSWORDS["cajero@vestidor.local"]),
                estado="ACTIVO",
            )
        )
        created += 1

    db.flush()
    return created


def _seed_catalog(db: Session) -> dict[str, int]:
    created = {
        "categorias": 0,
        "tallas": 0,
        "colores": 0,
        "sucursales": 0,
        "productos": 0,
        "variantes": 0,
        "inventarios": 0,
        "recursos_virtuales": 0,
    }

    categories: dict[str, Categoria] = {}
    for name, description in INITIAL_CATEGORIES:
        category, was_created = _get_or_create_named(db, Categoria, name, descripcion=description)
        categories[name] = category
        created["categorias"] += int(was_created)

    sizes: dict[str, Talla] = {}
    for name in INITIAL_SIZES:
        size, was_created = _get_or_create_named(db, Talla, name)
        sizes[name] = size
        created["tallas"] += int(was_created)

    colors: dict[str, Color] = {}
    for name in INITIAL_COLORS:
        color, was_created = _get_or_create_named(db, Color, name)
        colors[name] = color
        created["colores"] += int(was_created)

    branch, was_created = _get_or_create_named(
        db,
        Sucursal,
        INITIAL_BRANCH[0],
        direccion=INITIAL_BRANCH[1],
        estado="ACTIVA",
    )
    created["sucursales"] += int(was_created)

    for product_index, (name, description, category_name, price, color_name) in enumerate(INITIAL_PRODUCTS, start=1):
        product = db.scalar(select(Producto).where(Producto.nombre == name))
        if product is None:
            product = Producto(
                id_categoria=categories[category_name].id_categoria,
                nombre=name,
                descripcion=description,
                precio_base=price,
                estado="ACTIVO",
            )
            db.add(product)
            db.flush()
            created["productos"] += 1

        asset_url = f"/api/assets/fitting/prenda-{product_index}.svg"
        resource = db.scalar(select(RecursoVirtual).where(
            RecursoVirtual.id_producto == product.id_producto, RecursoVirtual.url_archivo == asset_url))
        if resource is None:
            db.add(RecursoVirtual(id_producto=product.id_producto, tipo_recurso="imagen",
                                  url_archivo=asset_url, estado="ACTIVO"))
            created["recursos_virtuales"] += 1

        # Keep the SVG illustration for the normal catalogue. The try-on
        # pipeline receives a separate raster cutout.
        tryon_url = f"/api/assets/tryon/prenda-{product_index}.png"
        tryon_resource = db.scalar(select(RecursoVirtual).where(
            RecursoVirtual.id_producto == product.id_producto,
            RecursoVirtual.url_archivo == tryon_url,
        ))
        if tryon_resource is None:
            db.add(RecursoVirtual(id_producto=product.id_producto, tipo_recurso="tryon",
                                  url_archivo=tryon_url, estado="ACTIVO"))
            created["recursos_virtuales"] += 1

        for size_name in INITIAL_SIZES:
            sku = f"VV-{product_index:03d}-{size_name}-{color_name[:3].upper()}"
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
                created["variantes"] += 1

            inventory = db.scalar(
                select(Inventario).where(
                    Inventario.id_sucursal == branch.id_sucursal,
                    Inventario.id_variante == variant.id_variante,
                )
            )
            if inventory is None:
                db.add(
                    Inventario(
                        id_sucursal=branch.id_sucursal,
                        id_variante=variant.id_variante,
                        stock_disponible=12,
                        stock_reservado=0,
                    )
                )
                created["inventarios"] += 1

    db.flush()
    return created


def seed_initial_data(db: Session) -> dict[str, int]:
    created = {"roles": seed_roles(db)}
    created["usuarios"] = _seed_users(db)
    created.update(_seed_catalog(db))
    created["ciudades"] = 0
    for city_name in db.scalars(select(Sucursal.ciudad).distinct()).all():
        _, added = _get_or_create_named(db, Ciudad, city_name)
        created["ciudades"] += int(added)
    branch = db.scalar(select(Sucursal).where(Sucursal.nombre == INITIAL_BRANCH[0]))
    for email in ("encargado@vestidor.local", "cajero@vestidor.local"):
        staff = db.scalar(select(Usuario).where(Usuario.correo == email))
        if staff and staff.id_sucursal is None:
            staff.id_sucursal = branch.id_sucursal
    supplier, added = _get_or_create_named(db, Proveedor, "Textiles Bolivia", contacto="contacto@textiles.example")
    created["proveedores"] = int(added)
    collection, added = _get_or_create_named(db, Coleccion, "Colección esencial", descripcion="Prendas para uso diario")
    created["colecciones"] = int(added)
    for product in db.scalars(select(Producto).where(Producto.nombre.in_([p[0] for p in INITIAL_PRODUCTS]))).all():
        if product.id_proveedor is None:
            product.id_proveedor = supplier.id_proveedor
        if product.id_coleccion is None:
            product.id_coleccion = collection.id_coleccion
    promotion = db.scalar(select(Promocion).where(Promocion.nombre == "Bienvenida"))
    created["promociones"] = int(promotion is None)
    if promotion is None:
        product = db.scalar(select(Producto).where(Producto.nombre == INITIAL_PRODUCTS[0][0]))
        db.add(Promocion(nombre="Bienvenida", id_producto=product.id_producto, descuento=Decimal("10"),
                        inicio=date.today(), fin=date.today() + timedelta(days=90)))
    db.flush()
    return created


def main() -> None:
    import argparse
    from app.core.config import settings
    parser = argparse.ArgumentParser(description="Initialize roles or development demo data")
    parser.add_argument("--roles-only", action="store_true")
    args = parser.parse_args()
    if settings.environment == "production" and not args.roles_only:
        parser.error("Demo data is disabled in production; use --roles-only")
    db = SessionLocal()
    try:
        created = {"roles": seed_roles(db)} if args.roles_only else seed_initial_data(db)
        db.commit()
        print(f"Seed completado: {created}")
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
