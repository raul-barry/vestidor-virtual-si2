from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.sucursal import Sucursal
from app.models.inventario import Inventario


class BranchRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all(self) -> list[Sucursal]:
        return list(self.db.scalars(select(Sucursal).order_by(Sucursal.nombre)).all())

    def get_by_id(self, id_sucursal: int) -> Sucursal | None:
        return self.db.get(Sucursal, id_sucursal)

    def get_by_name(self, nombre: str) -> Sucursal | None:
        return self.db.scalar(select(Sucursal).where(Sucursal.nombre == nombre))

    def create(self, sucursal: Sucursal) -> Sucursal:
        self.db.add(sucursal)
        self.db.flush()
        self.db.refresh(sucursal)
        return sucursal

    def update(self, sucursal: Sucursal, **values: object) -> Sucursal:
        for field, value in values.items():
            setattr(sucursal, field, value)
        self.db.flush()
        self.db.refresh(sucursal)
        return sucursal

    def delete(self, sucursal: Sucursal) -> None:
        self.db.delete(sucursal)
        self.db.flush()

    def is_used(self, id_sucursal: int) -> bool:
        count = self.db.scalar(
            select(func.count(Inventario.id_inventario))
            .where(Inventario.id_sucursal == id_sucursal)
        )
        return (count or 0) > 0
