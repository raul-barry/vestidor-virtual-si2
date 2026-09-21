from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.security import require_roles
from app.database.database import get_db
from app.models.usuario import Usuario
from app.schemas.cart import AddCartItemRequest, CartResponse, UpdateCartItemRequest
from app.services.cart_service import CartService

cart_router = APIRouter(prefix="/cart", tags=["Carrito"])


def get_cart_service_for_user(db: Session, current_user: Usuario) -> tuple[CartService, int]:
    service = CartService(db)
    return service, service.get_client_id_for_user(current_user.id_usuario)


@cart_router.get("", response_model=CartResponse, responses={401: {"description": "Token inválido"}})
def get_cart(
    db: Session = Depends(get_db), current_user: Usuario = Depends(require_roles("CLIENTE"))
) -> CartResponse:
    service, id_cliente = get_cart_service_for_user(db, current_user)
    return service.get_cart(id_cliente)


@cart_router.post(
    "/items",
    response_model=CartResponse,
    status_code=status.HTTP_200_OK,
    responses={401: {"description": "Token inválido"}, 404: {"description": "Variante no encontrada"}},
)
def add_item(
    request: AddCartItemRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("CLIENTE")),
) -> CartResponse:
    service, id_cliente = get_cart_service_for_user(db, current_user)
    return service.add_item(id_cliente, request.id_variante, request.cantidad)


@cart_router.put(
    "/items/{id_detalle}",
    response_model=CartResponse,
    responses={401: {"description": "Token inválido"}, 404: {"description": "Producto no encontrado"}},
)
def update_item_quantity(
    id_detalle: int,
    request: UpdateCartItemRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("CLIENTE")),
) -> CartResponse:
    service, id_cliente = get_cart_service_for_user(db, current_user)
    return service.update_quantity(id_cliente, id_detalle, request.cantidad)


@cart_router.delete(
    "/items/{id_detalle}",
    response_model=CartResponse,
    responses={401: {"description": "Token inválido"}, 404: {"description": "Producto no encontrado"}},
)
def remove_item(
    id_detalle: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("CLIENTE")),
) -> CartResponse:
    service, id_cliente = get_cart_service_for_user(db, current_user)
    return service.remove_item(id_cliente, id_detalle)
