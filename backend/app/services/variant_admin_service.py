from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.producto_variante import ProductoVariante
from app.repositories.variant_admin_repository import VariantAdminRepository
from app.schemas.variant_admin import CreateVariantRequest, UpdateVariantRequest, VariantAdminResponse


class VariantAdminService:
    def __init__(self, db: Session) -> None:
        self.repository = VariantAdminRepository(db)

    def list_variants(self, id_producto: int) -> list[VariantAdminResponse]:
        self._get_product(id_producto)
        return [self._to_response(variant) for variant in self.repository.get_variants_by_product(id_producto)]

    def create_variant(self, id_producto: int, request: CreateVariantRequest) -> VariantAdminResponse:
        self._get_product(id_producto)
        self._validate_size_and_color(request.id_talla, request.id_color)
        if self.repository.get_variant_by_sku(request.sku):
            raise AppException("Ya existe una variante con ese SKU", status_code=409)

        try:
            variant = self.repository.create_variant(
                ProductoVariante(
                    id_producto=id_producto,
                    id_talla=request.id_talla,
                    id_color=request.id_color,
                    sku=request.sku,
                    estado="ACTIVO",
                )
            )
            self.repository.db.commit()
            return self._to_response(self._get_variant(variant.id_variante))
        except SQLAlchemyError as exc:
            self.repository.db.rollback()
            raise AppException("No se pudo crear la variante", status_code=500) from exc

    def update_variant(self, id_variante: int, request: UpdateVariantRequest) -> VariantAdminResponse:
        variant = self._get_variant(id_variante)
        values = request.model_dump(exclude_none=True)
        if "sku" in values:
            duplicate = self.repository.get_variant_by_sku(values["sku"])
            if duplicate is not None and duplicate.id_variante != id_variante:
                raise AppException("Ya existe una variante con ese SKU", status_code=409)
        self._validate_size_and_color(values.get("id_talla"), values.get("id_color"))

        try:
            variant = self.repository.update_variant(variant, **values)
            self.repository.db.commit()
            return self._to_response(self._get_variant(variant.id_variante))
        except SQLAlchemyError as exc:
            self.repository.db.rollback()
            raise AppException("No se pudo actualizar la variante", status_code=500) from exc

    def disable_variant(self, id_variante: int) -> VariantAdminResponse:
        variant = self._get_variant(id_variante)
        try:
            variant = self.repository.disable_variant(variant)
            self.repository.db.commit()
            return self._to_response(self._get_variant(variant.id_variante))
        except SQLAlchemyError as exc:
            self.repository.db.rollback()
            raise AppException("No se pudo desactivar la variante", status_code=500) from exc

    def _get_product(self, id_producto: int):
        product = self.repository.get_product_by_id(id_producto)
        if product is None:
            raise AppException("Producto no encontrado", status_code=404)
        return product

    def _get_variant(self, id_variante: int) -> ProductoVariante:
        variant = self.repository.get_variant_by_id(id_variante)
        if variant is None:
            raise AppException("Variante no encontrada", status_code=404)
        return variant

    def _validate_size_and_color(self, id_talla: int | None, id_color: int | None) -> None:
        if id_talla is not None and self.repository.get_size_by_id(id_talla) is None:
            raise AppException("Talla no encontrada", status_code=404)
        if id_color is not None and self.repository.get_color_by_id(id_color) is None:
            raise AppException("Color no encontrado", status_code=404)

    @staticmethod
    def _to_response(variant: ProductoVariante) -> VariantAdminResponse:
        return VariantAdminResponse(
            id_variante=variant.id_variante,
            sku=variant.sku,
            producto=variant.producto.nombre,
            talla=variant.talla.nombre,
            color=variant.color.nombre,
            estado=variant.estado,
        )
