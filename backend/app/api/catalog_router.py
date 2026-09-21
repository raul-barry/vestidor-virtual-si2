from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.database import get_db
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
def get_products(db: Session = Depends(get_db)) -> list[ProductCatalogResponse]:
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
) -> list[ProductCatalogResponse]:
    return CatalogService(db).search_catalog(nombre, categoria, talla, color, precio_max)


@catalog_router.get(
    "/products/{id_producto}/variants",
    response_model=ProductVariantsResponse,
    responses={404: {"description": "Producto no encontrado"}},
)
def get_product_variants(
    id_producto: int, db: Session = Depends(get_db)
) -> ProductVariantsResponse:
    return CatalogService(db).get_variants(id_producto)


@catalog_router.get(
    "/products/{id_producto}/availability",
    response_model=AvailabilityResponse,
    responses={404: {"description": "Producto no encontrado"}},
)
def get_product_availability(
    id_producto: int, db: Session = Depends(get_db)
) -> AvailabilityResponse:
    return CatalogService(db).get_availability(id_producto)
