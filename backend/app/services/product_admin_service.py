from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.producto import Producto
from app.repositories.product_admin_repository import ProductAdminRepository
from app.schemas.product_admin import (
    AdminCategoryResponse,
    CreateProductRequest,
    ProductAdminResponse,
    UpdateProductRequest,
)


class ProductAdminService:
    def __init__(self, db: Session) -> None:
        self.repository = ProductAdminRepository(db)

    def list_products(self) -> list[ProductAdminResponse]:
        return [self._to_response(product) for product in self.repository.get_all_products()]

    def create_product(self, request: CreateProductRequest) -> ProductAdminResponse:
        if self.repository.get_product_by_name(request.nombre):
            raise AppException("Ya existe un producto con ese nombre", status_code=409)
        category = self.repository.get_category_by_id(request.id_categoria)
        if category is None:
            raise AppException("Categoría no encontrada", status_code=404)

        try:
            product = self.repository.create_product(
                Producto(
                    id_categoria=category.id_categoria,
                    nombre=request.nombre,
                    descripcion=request.descripcion,
                    precio_base=request.precio_base,
                    estado="ACTIVO",
                )
            )
            self.repository.db.commit()
            return self._to_response(product)
        except SQLAlchemyError as exc:
            self.repository.db.rollback()
            raise AppException("No se pudo crear el producto", status_code=500) from exc

    def update_product(self, id_producto: int, request: UpdateProductRequest) -> ProductAdminResponse:
        product = self._get_product(id_producto)
        values = request.model_dump(exclude_none=True)
        if "nombre" in values:
            duplicate = self.repository.get_product_by_name(values["nombre"])
            if duplicate is not None and duplicate.id_producto != id_producto:
                raise AppException("Ya existe un producto con ese nombre", status_code=409)
        if "id_categoria" in values and self.repository.get_category_by_id(values["id_categoria"]) is None:
            raise AppException("Categoría no encontrada", status_code=404)

        try:
            product = self.repository.update_product(product, **values)
            self.repository.db.commit()
            return self._to_response(product)
        except SQLAlchemyError as exc:
            self.repository.db.rollback()
            raise AppException("No se pudo actualizar el producto", status_code=500) from exc

    def disable_product(self, id_producto: int) -> ProductAdminResponse:
        product = self._get_product(id_producto)
        try:
            product = self.repository.disable_product(product)
            self.repository.db.commit()
            return self._to_response(product)
        except SQLAlchemyError as exc:
            self.repository.db.rollback()
            raise AppException("No se pudo desactivar el producto", status_code=500) from exc

    def _get_product(self, id_producto: int) -> Producto:
        product = self.repository.get_product_by_id(id_producto)
        if product is None:
            raise AppException("Producto no encontrado", status_code=404)
        return product

    @staticmethod
    def _to_response(product: Producto) -> ProductAdminResponse:
        return ProductAdminResponse(
            id_producto=product.id_producto,
            nombre=product.nombre,
            descripcion=product.descripcion,
            precio_base=product.precio_base,
            estado=product.estado,
            categoria=AdminCategoryResponse(
                id_categoria=product.categoria.id_categoria,
                nombre=product.categoria.nombre,
            ),
        )
