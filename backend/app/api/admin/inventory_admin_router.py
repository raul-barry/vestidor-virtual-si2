from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.security import get_current_staff
from app.core.security import require_branch
from app.models.inventario import Inventario
from fastapi import HTTPException
from app.database.database import get_db
from app.models.usuario import Usuario
from app.schemas.inventory_admin import (
    CreateInventoryRequest,
    InventoryMovementResponse,
    InventoryResponse,
    StockAdjustmentRequest,
    StockMovementRequest,
)
from app.services.inventory_admin_service import InventoryAdminService

inventory_admin_router = APIRouter(prefix="/admin/inventory", tags=["Administración de inventario"])


def check_inventory(db, user, inventory_id):
    inv = db.get(Inventario, inventory_id)
    if inv is None:
        raise HTTPException(404, "Inventario no encontrado")
    require_branch(user, inv.id_sucursal)


@inventory_admin_router.get("", response_model=list[InventoryResponse])
def list_inventory(
    db: Session = Depends(get_db), _: Usuario = Depends(get_current_staff)
) -> list[InventoryResponse]:
    service = InventoryAdminService(db)
    return [service._to_inventory_response(inv) for inv in service.repository.get_inventory()
            if _.rol.nombre == "ADMINISTRADOR" or (_.id_sucursal is not None and inv.id_sucursal == _.id_sucursal)]


@inventory_admin_router.post("", response_model=InventoryResponse, status_code=status.HTTP_201_CREATED)
def create_inventory(
    request: CreateInventoryRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_staff),
) -> InventoryResponse:
    require_branch(current_user, request.id_sucursal)
    return InventoryAdminService(db).create_stock(request, current_user.id_usuario)


@inventory_admin_router.post("/{id_inventario}/increase", response_model=InventoryResponse)
def increase_stock(
    id_inventario: int,
    request: StockMovementRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_staff),
) -> InventoryResponse:
    check_inventory(db, current_user, id_inventario)
    return InventoryAdminService(db).increase_stock(id_inventario, request, current_user.id_usuario)


@inventory_admin_router.post("/{id_inventario}/decrease", response_model=InventoryResponse)
def decrease_stock(
    id_inventario: int,
    request: StockMovementRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_staff),
) -> InventoryResponse:
    check_inventory(db, current_user, id_inventario)
    return InventoryAdminService(db).decrease_stock(id_inventario, request, current_user.id_usuario)


@inventory_admin_router.put("/{id_inventario}/adjust", response_model=InventoryResponse)
def adjust_stock(
    id_inventario: int,
    request: StockAdjustmentRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_staff),
) -> InventoryResponse:
    check_inventory(db, current_user, id_inventario)
    return InventoryAdminService(db).adjust_stock(id_inventario, request, current_user.id_usuario)


@inventory_admin_router.get("/{id_inventario}/movements", response_model=list[InventoryMovementResponse])
def get_movements(
    id_inventario: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_staff),
) -> list[InventoryMovementResponse]:
    check_inventory(db, _, id_inventario)
    return InventoryAdminService(db).get_history(id_inventario)
