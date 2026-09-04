from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_admin
from app.database.database import get_db
from app.models.usuario import Usuario
from app.schemas.order_admin import OrderAdminDetailResponse, OrderAdminResponse, UpdateOrderStatusRequest
from app.services.order_admin_service import OrderAdminService

order_admin_router = APIRouter(prefix="/admin/orders", tags=["Administración de pedidos"])


@order_admin_router.get("", response_model=list[OrderAdminResponse])
def list_orders(
    estado: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_admin),
) -> list[OrderAdminResponse]:
    return OrderAdminService(db).list_orders(estado)


@order_admin_router.get("/{id_pedido}", response_model=OrderAdminDetailResponse)
def get_order_detail(
    id_pedido: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_admin),
) -> OrderAdminDetailResponse:
    return OrderAdminService(db).get_order_detail(id_pedido)


@order_admin_router.put("/{id_pedido}/status", response_model=OrderAdminResponse)
def change_status(
    id_pedido: int,
    request: UpdateOrderStatusRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_admin),
) -> OrderAdminResponse:
    return OrderAdminService(db).change_status(id_pedido, request.estado, current_user.id_usuario)
