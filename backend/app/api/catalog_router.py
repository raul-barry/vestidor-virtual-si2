from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.core.security import get_optional_current_user
from app.core.tenancy import set_catalog_context
from app.models.usuario import Usuario
from app.schemas.catalog import AvailabilityResponse, ProductCatalogResponse, ProductVariantsResponse
from app.services.catalog_service import CatalogService

catalog_router = APIRouter(prefix="/catalog", tags=["Catalogo"])


@catalog_router.get(
    "/products",
    response_model=list[ProductCatalogResponse],
    response_model_exclude_none=True,
    responses={
        200: {
            "description": "Productos disponibles en el catálogo",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id_producto": 1,
                            "nombre": "Camisa Oxford",
                            "descripcion": "Camisa formal masculina",
                            "precio_base": "250.00",
                            "estado": "ACTIVO",
                            "categoria": {"id_categoria": 1, "nombre": "Camisas"},
                            "variantes": [
                                {
                                    "id_variante": 1,
                                    "sku": "CAM001-M-BLA",
                                    "talla": "M",
                                    "color": "Blanco",
                                }
                            ],
                        }
                    ]
                }
            },
        }
    },
)
def get_products(organization_slug: str | None = Query(default=None), db: Session = Depends(get_db), current_user: Usuario | None = Depends(get_optional_current_user)) -> list[ProductCatalogResponse]:
    set_catalog_context(db, organization_slug, current_user)
    return CatalogService(db).get_catalog()


@catalog_router.get(
    "/products/search",
    response_model=list[ProductCatalogResponse],
    response_model_exclude_none=True,
)
def search_products(
    nombre: str | None = Query(default=None),
    categoria: str | None = Query(default=None),
    talla: str | None = Query(default=None),
    color: str | None = Query(default=None),
    precio_max: Decimal | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    organization_slug: str | None = Query(default=None),
    current_user: Usuario | None = Depends(get_optional_current_user),
) -> list[ProductCatalogResponse]:
    set_catalog_context(db, organization_slug, current_user)
    return CatalogService(db).search_catalog(nombre, categoria, talla, color, precio_max)


@catalog_router.get(
    "/products/{id_producto}/variants",
    response_model=ProductVariantsResponse,
    responses={404: {"description": "Producto no encontrado"}},
)
def get_product_variants(
    id_producto: int, organization_slug: str | None = Query(default=None), db: Session = Depends(get_db), current_user: Usuario | None = Depends(get_optional_current_user)
) -> ProductVariantsResponse:
    set_catalog_context(db, organization_slug, current_user)
    return CatalogService(db).get_variants(id_producto)


@catalog_router.get(
    "/products/{id_producto}/availability",
    response_model=AvailabilityResponse,
    responses={404: {"description": "Producto no encontrado"}},
)
def get_product_availability(
    id_producto: int, organization_slug: str | None = Query(default=None), db: Session = Depends(get_db), current_user: Usuario | None = Depends(get_optional_current_user)
) -> AvailabilityResponse:
    set_catalog_context(db, organization_slug, current_user)
    return CatalogService(db).get_availability(id_producto)
