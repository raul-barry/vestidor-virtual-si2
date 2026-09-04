from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.inventario import Inventario
from app.models.movimiento_inventario import MovimientoInventario
from app.repositories.inventory_admin_repository import InventoryAdminRepository
from app.schemas.inventory_admin import (
    CreateInventoryRequest,
    InventoryMovementResponse,
    InventoryResponse,
    StockAdjustmentRequest,
    StockMovementRequest,
)


class InventoryAdminService:
    def __init__(self, db: Session) -> None:
        self.repository = InventoryAdminRepository(db)

    def list_inventory(self) -> list[InventoryResponse]:
        return [self._to_inventory_response(inventory) for inventory in self.repository.get_inventory()]

    def create_stock(self, request: CreateInventoryRequest, id_usuario: int) -> InventoryResponse:
        if self.repository.get_variant_by_id(request.id_variante) is None:
            raise AppException("Variante no encontrada", status_code=404)
        if self.repository.get_branch_by_id(request.id_sucursal) is None:
            raise AppException("Sucursal no encontrada", status_code=404)
        if self.repository.get_inventory_by_branch_and_variant(request.id_sucursal, request.id_variante):
            raise AppException("La variante ya tiene inventario en esta sucursal", status_code=409)

        try:
            inventory = self.repository.create_inventory(
                Inventario(
                    id_sucursal=request.id_sucursal,
                    id_variante=request.id_variante,
                    stock_disponible=request.stock,
                    stock_reservado=0,
                )
            )
            self._create_movement(inventory, "AJUSTE", request.stock, 0, request.stock, "Stock inicial", id_usuario)
            self.repository.db.commit()
            return self._to_inventory_response(self._get_inventory(inventory.id_inventario))
        except SQLAlchemyError as exc:
            self.repository.db.rollback()
            raise AppException("No se pudo crear el inventario", status_code=500) from exc

    def increase_stock(self, id_inventario: int, request: StockMovementRequest, id_usuario: int) -> InventoryResponse:
        self._validate_movement_type(request, "ENTRADA")
        return self._change_stock(id_inventario, request.cantidad, "ENTRADA", request.motivo, id_usuario)

    def decrease_stock(self, id_inventario: int, request: StockMovementRequest, id_usuario: int) -> InventoryResponse:
        self._validate_movement_type(request, "SALIDA")
        return self._change_stock(id_inventario, -request.cantidad, "SALIDA", request.motivo, id_usuario)

    def adjust_stock(self, id_inventario: int, request: StockAdjustmentRequest, id_usuario: int) -> InventoryResponse:
        inventory = self._get_inventory(id_inventario)
        previous_stock = inventory.stock_disponible
        quantity = request.nuevo_stock - previous_stock
        try:
            self.repository.update_stock(inventory, request.nuevo_stock)
            self._create_movement(
                inventory,
                "AJUSTE",
                quantity,
                previous_stock,
                request.nuevo_stock,
                request.motivo,
                id_usuario,
            )
            self.repository.db.commit()
            return self._to_inventory_response(self._get_inventory(id_inventario))
        except SQLAlchemyError as exc:
            self.repository.db.rollback()
            raise AppException("No se pudo ajustar el inventario", status_code=500) from exc

    def get_history(self, id_inventario: int) -> list[InventoryMovementResponse]:
        self._get_inventory(id_inventario)
        return [
            InventoryMovementResponse(
                tipo=movement.tipo_movimiento,
                cantidad=movement.cantidad,
                stock_anterior=movement.stock_anterior,
                stock_nuevo=movement.stock_nuevo,
                fecha=movement.fecha_movimiento,
                usuario=f"{movement.usuario.nombres} {movement.usuario.apellidos}",
            )
            for movement in self.repository.get_movements(id_inventario)
        ]

    def _change_stock(
        self, id_inventario: int, delta: int, movement_type: str, motivo: str, id_usuario: int
    ) -> InventoryResponse:
        inventory = self._get_inventory(id_inventario)
        previous_stock = inventory.stock_disponible
        new_stock = previous_stock + delta
        if new_stock < 0:
            raise AppException("No se permite stock negativo", status_code=422)

        try:
            self.repository.update_stock(inventory, new_stock)
            self._create_movement(
                inventory,
                movement_type,
                abs(delta),
                previous_stock,
                new_stock,
                motivo,
                id_usuario,
            )
            self.repository.db.commit()
            return self._to_inventory_response(self._get_inventory(id_inventario))
        except SQLAlchemyError as exc:
            self.repository.db.rollback()
            raise AppException("No se pudo actualizar el inventario", status_code=500) from exc

    def _get_inventory(self, id_inventario: int) -> Inventario:
        inventory = self.repository.get_inventory_by_id(id_inventario)
        if inventory is None:
            raise AppException("Inventario no encontrado", status_code=404)
        return inventory

    @staticmethod
    def _validate_movement_type(request: StockMovementRequest, expected_type: str) -> None:
        if request.tipo_movimiento is not None and request.tipo_movimiento != expected_type:
            raise AppException("Tipo de movimiento no válido para esta operación", status_code=422)

    def _create_movement(
        self,
        inventory: Inventario,
        movement_type: str,
        quantity: int,
        previous_stock: int,
        new_stock: int,
        motivo: str,
        id_usuario: int,
    ) -> None:
        self.repository.create_movement(
            MovimientoInventario(
                id_inventario=inventory.id_inventario,
                tipo_movimiento=movement_type,
                cantidad=quantity,
                stock_anterior=previous_stock,
                stock_nuevo=new_stock,
                motivo=motivo,
                id_usuario=id_usuario,
            )
        )

    @staticmethod
    def _to_inventory_response(inventory: Inventario) -> InventoryResponse:
        return InventoryResponse(
            id_inventario=inventory.id_inventario,
            producto=inventory.variante.producto.nombre,
            sku=inventory.variante.sku,
            talla=inventory.variante.talla.nombre,
            color=inventory.variante.color.nombre,
            sucursal=inventory.sucursal.nombre,
            stock=inventory.stock_disponible,
            stock_bajo=inventory.stock_disponible < 5,
        )
