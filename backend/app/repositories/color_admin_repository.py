from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.color import Color


class ColorRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all(self) -> list[Color]:
        return list(self.db.scalars(select(Color).order_by(Color.nombre)).all())

    def get_by_id(self, id_color: int) -> Color | None:
        return self.db.get(Color, id_color)

    def get_by_name(self, nombre: str) -> Color | None:
        return self.db.scalar(select(Color).where(Color.nombre == nombre))

    def create(self, color: Color) -> Color:
        self.db.add(color)
        self.db.flush()
        self.db.refresh(color)
        return color

    def update(self, color: Color, **values: object) -> Color:
        for field, value in values.items():
            setattr(color, field, value)
        self.db.flush()
        self.db.refresh(color)
        return color

    def delete(self, color: Color) -> None:
        self.db.delete(color)
        self.db.flush()

    def is_used(self, id_color: int) -> bool:
        from app.models.producto_variante import ProductoVariante
        count = self.db.scalar(
            select(func.count(ProductoVariante.id_variante))
            .where(ProductoVariante.id_color == id_color)
        )
        return (count or 0) > 0
