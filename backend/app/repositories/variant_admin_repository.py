from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.color import Color
from app.models.producto import Producto
from app.models.producto_variante import ProductoVariante
from app.models.talla import Talla


class VariantAdminRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_variants_by_product(self, id_producto: int) -> list[ProductoVariante]:
        statement = (
            select(ProductoVariante)
            .where(ProductoVariante.id_producto == id_producto)
            .options(
                joinedload(ProductoVariante.producto),
                joinedload(ProductoVariante.talla),
                joinedload(ProductoVariante.color),
            )
            .order_by(ProductoVariante.id_variante)
        )
        return list(self.db.scalars(statement).all())

    def get_variant_by_id(self, id_variante: int) -> ProductoVariante | None:
        statement = (
            select(ProductoVariante)
            .where(ProductoVariante.id_variante == id_variante)
            .options(
                joinedload(ProductoVariante.producto),
                joinedload(ProductoVariante.talla),
                joinedload(ProductoVariante.color),
            )
        )
        return self.db.scalar(statement)

    def get_variant_by_sku(self, sku: str) -> ProductoVariante | None:
        statement = select(ProductoVariante).where(ProductoVariante.sku == sku)
        return self.db.scalar(statement)

    def get_product_by_id(self, id_producto: int) -> Producto | None:
        return self.db.get(Producto, id_producto)

    def get_size_by_id(self, id_talla: int) -> Talla | None:
        return self.db.get(Talla, id_talla)

    def get_color_by_id(self, id_color: int) -> Color | None:
        return self.db.get(Color, id_color)

    def create_variant(self, variant: ProductoVariante) -> ProductoVariante:
        self.db.add(variant)
        self.db.flush()
        self.db.refresh(variant)
        return variant

    def update_variant(self, variant: ProductoVariante, **values: object) -> ProductoVariante:
        for field, value in values.items():
            setattr(variant, field, value)
        self.db.flush()
        self.db.refresh(variant)
        return variant

    def disable_variant(self, variant: ProductoVariante) -> ProductoVariante:
        variant.estado = "INACTIVO"
        self.db.flush()
        self.db.refresh(variant)
        return variant
