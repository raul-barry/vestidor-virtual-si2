from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.database import SessionLocal
from app.models.categoria import Categoria
from app.models.color import Color
from app.models.sucursal import Sucursal
from app.models.talla import Talla

INITIAL_CATEGORIES = ("Camisas", "Pantalones", "Chaquetas", "Poleras", "Zapatos")
INITIAL_SIZES = ("XS", "S", "M", "L", "XL", "XXL")
INITIAL_COLORS = ("Negro", "Blanco", "Azul", "Gris", "Rojo")
INITIAL_BRANCHES = (
    ("Sucursal Central", "Av. Principal 100"),
    ("Sucursal Norte", "Av. Norte 250"),
)


def _seed_named_records(db: Session, model, names: Iterable[str]) -> int:
    values = tuple(names)
    existing = set(db.scalars(select(model.nombre).where(model.nombre.in_(values))).all())
    records = [model(nombre=name) for name in values if name not in existing]
    if records:
        db.add_all(records)
        db.flush()
    return len(records)


def seed_catalog_data(db: Session) -> dict[str, int]:
    created = {
        "categorias": _seed_named_records(db, Categoria, INITIAL_CATEGORIES),
        "tallas": _seed_named_records(db, Talla, INITIAL_SIZES),
        "colores": _seed_named_records(db, Color, INITIAL_COLORS),
    }
    branch_names = tuple(name for name, _ in INITIAL_BRANCHES)
    existing_branches = set(
        db.scalars(select(Sucursal.nombre).where(Sucursal.nombre.in_(branch_names))).all()
    )
    branches = [
        Sucursal(nombre=name, direccion=address, estado="ACTIVA")
        for name, address in INITIAL_BRANCHES
        if name not in existing_branches
    ]
    if branches:
        db.add_all(branches)
        db.flush()
    created["sucursales"] = len(branches)
    return created


def main() -> None:
    db = SessionLocal()
    try:
        created = seed_catalog_data(db)
        db.commit()
        print(f"Seed de catálogo completado: {created}")
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
