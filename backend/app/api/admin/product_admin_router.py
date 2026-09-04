from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.security import get_current_admin
from app.database.database import get_db
from app.schemas.product_admin import CreateProductRequest, ProductAdminResponse, UpdateProductRequest
from app.services.product_admin_service import ProductAdminService

product_admin_router = APIRouter(prefix="/admin/products", tags=["Administración de productos"])


@product_admin_router.get("", response_model=list[ProductAdminResponse])
def list_products(
    db: Session = Depends(get_db), _: object = Depends(get_current_admin)
) -> list[ProductAdminResponse]:
    return ProductAdminService(db).list_products()


@product_admin_router.post("", response_model=ProductAdminResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    request: CreateProductRequest,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_admin),
) -> ProductAdminResponse:
    return ProductAdminService(db).create_product(request)


@product_admin_router.put("/{id_producto}", response_model=ProductAdminResponse)
def update_product(
    id_producto: int,
    request: UpdateProductRequest,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_admin),
) -> ProductAdminResponse:
    return ProductAdminService(db).update_product(id_producto, request)


@product_admin_router.delete("/{id_producto}", response_model=ProductAdminResponse)
def disable_product(
    id_producto: int,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_admin),
) -> ProductAdminResponse:
    return ProductAdminService(db).disable_product(id_producto)
