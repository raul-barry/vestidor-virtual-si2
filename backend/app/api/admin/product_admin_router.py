from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_current_admin
from app.database.database import get_db
from app.models.producto import Producto
from app.models.recurso_virtual import RecursoVirtual
from app.schemas.product_admin import CreateProductRequest, ProductAdminResponse, UpdateProductRequest
from app.services.image_storage import LocalImageStorage
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


@product_admin_router.post("/{id_producto}/image")
async def upload_product_image(
    id_producto: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: object = Depends(get_current_admin),
) -> dict[str, str]:
    if not db.get(Producto, id_producto):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")

    storage = LocalImageStorage()
    url = await storage.save(file)
    resources = db.scalars(
        select(RecursoVirtual).where(
            RecursoVirtual.id_producto == id_producto,
            RecursoVirtual.tipo_recurso == "imagen",
            RecursoVirtual.estado == "ACTIVO",
        )
    ).all()
    try:
        for resource in resources:
            resource.estado = "INACTIVO"
        db.add(
            RecursoVirtual(
                id_producto=id_producto,
                tipo_recurso="imagen",
                url_archivo=url,
                estado="ACTIVO",
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        storage.delete(url)
        raise

    for resource in resources:
        storage.delete(resource.url_archivo)
    return {"imagen_url": url}


@product_admin_router.delete("/{id_producto}/image", status_code=status.HTTP_204_NO_CONTENT)
def delete_product_image(
    id_producto: int,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_admin),
) -> None:
    if not db.get(Producto, id_producto):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
    storage = LocalImageStorage()
    resources = db.scalars(
        select(RecursoVirtual).where(
            RecursoVirtual.id_producto == id_producto,
            RecursoVirtual.tipo_recurso == "imagen",
            RecursoVirtual.estado == "ACTIVO",
        )
    ).all()
    for resource in resources:
        resource.estado = "INACTIVO"
    db.commit()
    for resource in resources:
        storage.delete(resource.url_archivo)
