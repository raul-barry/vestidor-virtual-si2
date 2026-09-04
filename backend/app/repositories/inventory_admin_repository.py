from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.inventario import Inventario
from app.models.movimiento_inventario import MovimientoInventario
from app.models.producto_variante import ProductoVariante
from app.models.sucursal import Sucursal


class InventoryAdminRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_inventory(self) -> list[Inventario]:
        statement = (
            select(Inventario)
            .options(
                joinedload(Inventario.sucursal),
                joinedload(Inventario.variante).joinedload(ProductoVariante.producto),
                joinedload(Inventario.variante).joinedload(ProductoVariante.talla),
                joinedload(Inventario.variante).joinedload(ProductoVariante.color),
            )
            .order_by(Sucursal.nombre, Inventario.id_inventario)
            .join(Inventario.sucursal)
        )
        return list(self.db.scalars(statement).all())

    def get_inventory_by_id(self, id_inventario: int) -> Inventario | None:
        statement = (
            select(Inventario)
            .where(Inventario.id_inventario == id_inventario)
            .options(
                joinedload(Inventario.sucursal),
                joinedload(Inventario.variante).joinedload(ProductoVariante.producto),
                joinedload(Inventario.variante).joinedload(ProductoVariante.talla),
                joinedload(Inventario.variante).joinedload(ProductoVariante.color),
            )
        )
        return self.db.scalar(statement)

    def get_inventory_by_branch_and_variant(self, id_sucursal: int, id_variante: int) -> Inventario | None:
        statement = select(Inventario).where(
            Inventario.id_sucursal == id_sucursal,
            Inventario.id_variante == id_variante,
        )
        return self.db.scalar(statement)

    def get_variant_by_id(self, id_variante: int) -> ProductoVariante | None:
        return self.db.get(ProductoVariante, id_variante)

    def get_branch_by_id(self, id_sucursal: int) -> Sucursal | None:
        return self.db.get(Sucursal, id_sucursal)

    def create_inventory(self, inventory: Inventario) -> Inventario:
        self.db.add(inventory)
        self.db.flush()
        self.db.refresh(inventory)
        return inventory

    def update_stock(self, inventory: Inventario, stock: int) -> Inventario:
        inventory.stock_disponible = stock
        self.db.flush()
        self.db.refresh(inventory)
        return inventory

    def create_movement(self, movement: MovimientoInventario) -> MovimientoInventario:
        self.db.add(movement)
        self.db.flush()
        self.db.refresh(movement)
        return movement

    def get_movements(self, id_inventario: int) -> list[MovimientoInventario]:
        statement = (
            select(MovimientoInventario)
            .where(MovimientoInventario.id_inventario == id_inventario)
            .options(joinedload(MovimientoInventario.usuario))
            .order_by(MovimientoInventario.fecha_movimiento.desc())
        )
        return list(self.db.scalars(statement).all())
