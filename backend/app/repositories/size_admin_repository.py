from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.talla import Talla


class SizeRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all(self) -> list[Talla]:
        return list(self.db.scalars(select(Talla).order_by(Talla.nombre)).all())

    def get_by_id(self, id_talla: int) -> Talla | None:
        return self.db.get(Talla, id_talla)

    def get_by_name(self, nombre: str) -> Talla | None:
        return self.db.scalar(select(Talla).where(Talla.nombre == nombre))

    def create(self, talla: Talla) -> Talla:
        self.db.add(talla)
        self.db.flush()
        self.db.refresh(talla)
        return talla

    def update(self, talla: Talla, **values: object) -> Talla:
        for field, value in values.items():
            setattr(talla, field, value)
        self.db.flush()
        self.db.refresh(talla)
        return talla

    def delete(self, talla: Talla) -> None:
        self.db.delete(talla)
        self.db.flush()

    def is_used(self, id_talla: int) -> bool:
        from app.models.producto_variante import ProductoVariante
        count = self.db.scalar(
            select(func.count(ProductoVariante.id_variante))
            .where(ProductoVariante.id_talla == id_talla)
        )
        return (count or 0) > 0
