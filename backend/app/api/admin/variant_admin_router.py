from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.security import get_current_admin
from app.database.database import get_db
from app.schemas.variant_admin import CreateVariantRequest, UpdateVariantRequest, VariantAdminResponse
from app.services.variant_admin_service import VariantAdminService

variant_admin_router = APIRouter(prefix="/admin", tags=["Administración de variantes"])


@variant_admin_router.get("/variants", response_model=list[VariantAdminResponse])
def list_all_variants(db: Session = Depends(get_db), _: object = Depends(get_current_admin)) -> list[VariantAdminResponse]:
    from app.models.producto_variante import ProductoVariante
    from sqlalchemy import select
    rows = db.scalars(select(ProductoVariante).order_by(ProductoVariante.id_variante)).all()
    return [VariantAdminResponse(id_variante=row.id_variante, sku=row.sku, producto=row.producto.nombre,
                                talla=row.talla.nombre, color=row.color.nombre, estado=row.estado) for row in rows]


@variant_admin_router.get("/products/{id_producto}/variants", response_model=list[VariantAdminResponse])
def list_variants(
    id_producto: int,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_admin),
) -> list[VariantAdminResponse]:
    return VariantAdminService(db).list_variants(id_producto)


@variant_admin_router.post(
    "/products/{id_producto}/variants",
    response_model=VariantAdminResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_variant(
    id_producto: int,
    request: CreateVariantRequest,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_admin),
) -> VariantAdminResponse:
    return VariantAdminService(db).create_variant(id_producto, request)


@variant_admin_router.post(
    "/variants",
    response_model=VariantAdminResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_variant_direct(
    request: CreateVariantRequest,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_admin),
) -> VariantAdminResponse:
    from fastapi import HTTPException
    if not request.id_producto:
        raise HTTPException(status_code=400, detail="id_producto es requerido")
    return VariantAdminService(db).create_variant(request.id_producto, request)


@variant_admin_router.put("/variants/{id_variante}", response_model=VariantAdminResponse)
def update_variant(
    id_variante: int,
    request: UpdateVariantRequest,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_admin),
) -> VariantAdminResponse:
    return VariantAdminService(db).update_variant(id_variante, request)


@variant_admin_router.delete("/variants/{id_variante}", response_model=VariantAdminResponse)
def disable_variant(
    id_variante: int,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_admin),
) -> VariantAdminResponse:
    return VariantAdminService(db).disable_variant(id_variante)
