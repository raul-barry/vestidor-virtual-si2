from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.categoria import Categoria


class CategoryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all(self) -> list[Categoria]:
        return list(self.db.scalars(select(Categoria).order_by(Categoria.nombre)).all())

    def get_by_id(self, id_categoria: int) -> Categoria | None:
        return self.db.get(Categoria, id_categoria)

    def get_by_name(self, nombre: str) -> Categoria | None:
        return self.db.scalar(select(Categoria).where(Categoria.nombre == nombre))

    def create(self, categoria: Categoria) -> Categoria:
        self.db.add(categoria)
        self.db.flush()
        self.db.refresh(categoria)
        return categoria

    def update(self, categoria: Categoria, **values: object) -> Categoria:
        for field, value in values.items():
            setattr(categoria, field, value)
        self.db.flush()
        self.db.refresh(categoria)
        return categoria

    def delete(self, categoria: Categoria) -> None:
        self.db.delete(categoria)
        self.db.flush()

    def is_used(self, id_categoria: int) -> bool:
        from app.models.producto import Producto
        count = self.db.scalar(
            select(func.count(Producto.id_producto))
            .where(Producto.id_categoria == id_categoria)
        )
        return (count or 0) > 0
