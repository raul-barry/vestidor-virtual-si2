from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.categoria import Categoria
from app.models.producto import Producto


class ProductAdminRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all_products(self) -> list[Producto]:
        statement = select(Producto).options(joinedload(Producto.categoria)).order_by(Producto.id_producto)
        return list(self.db.scalars(statement).all())

    def get_product_by_id(self, id_producto: int) -> Producto | None:
        statement = select(Producto).where(Producto.id_producto == id_producto).options(joinedload(Producto.categoria))
        return self.db.scalar(statement)

    def get_product_by_name(self, nombre: str) -> Producto | None:
        statement = select(Producto).where(Producto.nombre == nombre)
        return self.db.scalar(statement)

    def get_category_by_id(self, id_categoria: int) -> Categoria | None:
        return self.db.get(Categoria, id_categoria)

    def create_product(self, producto: Producto) -> Producto:
        self.db.add(producto)
        self.db.flush()
        self.db.refresh(producto)
        return producto

    def update_product(self, producto: Producto, **values: object) -> Producto:
        for field, value in values.items():
            setattr(producto, field, value)
        self.db.flush()
        self.db.refresh(producto)
        return producto

    def disable_product(self, producto: Producto) -> Producto:
        producto.estado = "INACTIVO"
        self.db.flush()
        self.db.refresh(producto)
        return producto
