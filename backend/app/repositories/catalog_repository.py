from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.categoria import Categoria
from app.models.color import Color
from app.models.inventario import Inventario
from app.models.producto import Producto
from app.models.producto_variante import ProductoVariante
from app.models.talla import Talla
from app.models.sucursal import Sucursal


class CatalogRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all_products(self) -> list[Producto]:
        statement = select(Producto).options(
            joinedload(Producto.categoria),
            selectinload(Producto.variantes).joinedload(ProductoVariante.talla),
            selectinload(Producto.variantes).joinedload(ProductoVariante.color),
        )
        return list(self.db.scalars(statement).unique().all())

    def search_products(
        self,
        nombre: str | None = None,
        categoria: str | None = None,
        talla: str | None = None,
        color: str | None = None,
        precio_max: Decimal | None = None,
    ) -> list[Producto]:
        statement = select(Producto)
        if nombre:
            statement = statement.where(Producto.nombre.ilike(f"%{nombre}%"))
        if categoria:
            statement = statement.join(Producto.categoria).where(Categoria.nombre.ilike(f"%{categoria}%"))
        if talla or color:
            statement = statement.join(Producto.variantes)
        if talla:
            statement = statement.join(ProductoVariante.talla).where(Talla.nombre.ilike(f"%{talla}%"))
        if color:
            statement = statement.join(ProductoVariante.color).where(Color.nombre.ilike(f"%{color}%"))
        if precio_max is not None:
            statement = statement.where(Producto.precio_base <= precio_max)

        statement = statement.options(
            joinedload(Producto.categoria),
            selectinload(Producto.variantes).joinedload(ProductoVariante.talla),
            selectinload(Producto.variantes).joinedload(ProductoVariante.color),
        )
        return list(self.db.scalars(statement).unique().all())

    def get_product_variants(self, product_id: int) -> Producto | None:
        statement = (
            select(Producto)
            .where(Producto.id_producto == product_id)
            .options(
                selectinload(Producto.variantes).joinedload(ProductoVariante.talla),
                selectinload(Producto.variantes).joinedload(ProductoVariante.color),
            )
        )
        return self.db.scalar(statement)

    def get_product_availability(
        self, product_id: int
    ) -> tuple[Producto | None, list[tuple[int, str, str, int]]]:
        product = self.db.get(Producto, product_id)
        if product is None:
            return None, []

        statement = (
            select(
                Sucursal.id_sucursal,
                Sucursal.nombre,
                Sucursal.direccion,
                func.sum(Inventario.stock_disponible).label("stock_disponible"),
            )
            .select_from(Inventario)
            .join(Sucursal, Inventario.id_sucursal == Sucursal.id_sucursal)
            .join(ProductoVariante, Inventario.id_variante == ProductoVariante.id_variante)
            .where(
                ProductoVariante.id_producto == product_id,
                Inventario.stock_disponible > 0,
            )
            .group_by(Sucursal.id_sucursal, Sucursal.nombre, Sucursal.direccion)
            .order_by(Sucursal.nombre)
        )
        availability = [tuple(row) for row in self.db.execute(statement).all()]
        return product, availability
