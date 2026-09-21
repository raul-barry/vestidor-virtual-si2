from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.producto import Producto
from app.models.recurso_virtual import RecursoVirtual
from app.repositories.catalog_repository import CatalogRepository
from app.services.pricing_service import current_price
from app.schemas.catalog import (
    AvailabilityResponse,
    BranchAvailabilityResponse,
    CategoryResponse,
    ProductCatalogResponse,
    ProductVariantsResponse,
    VariantResponse,
)


class CatalogService:
    def __init__(self, db: Session) -> None:
        self.repository = CatalogRepository(db)

    def get_catalog(self) -> list[ProductCatalogResponse]:
        return self._to_response(self.repository.get_all_products())

    def search_catalog(
        self,
        nombre: str | None = None,
        categoria: str | None = None,
        talla: str | None = None,
        color: str | None = None,
        precio_max: Decimal | None = None,
    ) -> list[ProductCatalogResponse]:
        if precio_max is not None and precio_max <= 0:
            raise AppException("precio_max debe ser positivo", status_code=422)
        products = self._to_response(self.repository.search_products(nombre, categoria, talla, color, None))
        return [p for p in products if precio_max is None or p.precio_base <= precio_max]

    def get_variants(self, id_producto: int) -> ProductVariantsResponse:
        product = self.repository.get_product_variants(id_producto)
        if product is None:
            raise AppException("Producto no encontrado", status_code=404)

        variants = [
            VariantResponse(
                id_variante=variant.id_variante,
                sku=variant.sku,
                talla=variant.talla.nombre,
                color=variant.color.nombre,
            )
            for variant in sorted(product.variantes, key=lambda variant: variant.id_variante)
        ]
        return ProductVariantsResponse(
            id_producto=product.id_producto,
            nombre_producto=product.nombre,
            tallas=sorted({variant.talla for variant in variants}),
            colores=sorted({variant.color for variant in variants}),
            variantes=variants,
        )

    def get_availability(self, id_producto: int) -> AvailabilityResponse:
        product, availability = self.repository.get_product_availability(id_producto)
        if product is None:
            raise AppException("Producto no encontrado", status_code=404)

        return AvailabilityResponse(
            id_producto=product.id_producto,
            nombre_producto=product.nombre,
            disponibilidad=[
                BranchAvailabilityResponse(
                    id_sucursal=id_sucursal,
                    nombre_sucursal=nombre_sucursal,
                    direccion=direccion,
                    stock_disponible=stock_disponible,
                )
                for id_sucursal, nombre_sucursal, direccion, stock_disponible in availability
            ],
        )

    def _to_response(self, products: list[Producto]) -> list[ProductCatalogResponse]:
        product_ids = [product.id_producto for product in products]
        image_by_product = {
            resource.id_producto: resource.url_archivo
            for resource in self.repository.db.scalars(
                select(RecursoVirtual).where(
                    RecursoVirtual.id_producto.in_(product_ids),
                    RecursoVirtual.tipo_recurso == "imagen",
                    RecursoVirtual.estado == "ACTIVO",
                ).order_by(RecursoVirtual.id)
            )
        } if product_ids else {}
        return [
            ProductCatalogResponse(
                id_producto=product.id_producto,
                nombre=product.nombre,
                descripcion=product.descripcion,
                precio_base=current_price(self.repository.db, product),
                estado=product.estado,
                categoria=CategoryResponse(
                    id_categoria=product.categoria.id_categoria,
                    nombre=product.categoria.nombre,
                ),
                variantes=[
                    VariantResponse(
                        id_variante=variant.id_variante,
                        sku=variant.sku,
                        talla=variant.talla.nombre,
                        color=variant.color.nombre,
                    )
                    for variant in product.variantes if variant.estado == "ACTIVO"
                ],
                imagen_url=image_by_product.get(product.id_producto),
            )
            for product in products if product.estado == "ACTIVO"
        ]
