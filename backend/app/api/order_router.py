from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database.database import get_db
from app.models.usuario import Usuario
from app.schemas.order import CreateOrderResponse, OrderDetailResponse, OrderSummaryResponse
from app.services.order_service import OrderService

order_router = APIRouter(prefix="/orders", tags=["Pedidos"])


def get_order_service_for_user(db: Session, current_user: Usuario) -> tuple[OrderService, int]:
    service = OrderService(db)
    return service, service.get_client_id_for_user(current_user.id_usuario)


@order_router.post(
    "",
    response_model=CreateOrderResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Carrito vacío"},
        401: {"description": "Token inválido"},
        404: {"description": "Carrito activo no encontrado"},
    },
)
def create_order(
    db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)
) -> CreateOrderResponse:
    service, id_cliente = get_order_service_for_user(db, current_user)
    order = service.create_order_from_cart(id_cliente)
    return CreateOrderResponse(id_pedido=order.id_pedido, estado=order.estado, total=order.total)


@order_router.get("", response_model=list[OrderSummaryResponse], responses={401: {"description": "Token inválido"}})
def get_orders(
    db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)
) -> list[OrderSummaryResponse]:
    service, id_cliente = get_order_service_for_user(db, current_user)
    return [
        OrderSummaryResponse(
            id_pedido=order.id_pedido,
            fecha_pedido=order.fecha_pedido,
            estado=order.estado,
            total=order.total,
        )
        for order in service.get_client_orders(id_cliente)
    ]


@order_router.get(
    "/{id_pedido}",
    response_model=OrderDetailResponse,
    responses={401: {"description": "Token inválido"}, 404: {"description": "Pedido no encontrado"}},
)
def get_order_detail(
    id_pedido: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> OrderDetailResponse:
    service, id_cliente = get_order_service_for_user(db, current_user)
    return service.get_order_detail(id_cliente, id_pedido)
