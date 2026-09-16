from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.categoria import Categoria
from app.repositories.category_admin_repository import CategoryRepository
from app.schemas.category_admin import CategoryAdminResponse, CreateCategoryRequest, UpdateCategoryRequest


class CategoryAdminService:
    def __init__(self, db: Session) -> None:
        self.repository = CategoryRepository(db)

    def list(self) -> list[CategoryAdminResponse]:
        return [self._to_response(c) for c in self.repository.get_all()]

    def get_by_id(self, id_categoria: int) -> CategoryAdminResponse:
        categoria = self.repository.get_by_id(id_categoria)
        if categoria is None:
            raise AppException("Categoría no encontrada", status_code=404)
        return self._to_response(categoria)

    def create(self, request: CreateCategoryRequest) -> CategoryAdminResponse:
        if self.repository.get_by_name(request.nombre):
            raise AppException("Ya existe una categoría con ese nombre", status_code=409)
        try:
            categoria = self.repository.create(
                Categoria(
                    nombre=request.nombre,
                    descripcion=request.descripcion,
                    estado=request.estado or "ACTIVO",
                )
            )
            self.repository.db.commit()
            return self._to_response(categoria)
        except SQLAlchemyError as exc:
            self.repository.db.rollback()
            raise AppException("No se pudo crear la categoría", status_code=500) from exc

    def update(self, id_categoria: int, request: UpdateCategoryRequest) -> CategoryAdminResponse:
        categoria = self.repository.get_by_id(id_categoria)
        if categoria is None:
            raise AppException("Categoría no encontrada", status_code=404)
        values = request.model_dump(exclude_none=True)
        if "nombre" in values:
            existing = self.repository.get_by_name(values["nombre"])
            if existing is not None and existing.id_categoria != id_categoria:
                raise AppException("Ya existe una categoría con ese nombre", status_code=409)
        try:
            categoria = self.repository.update(categoria, **values)
            self.repository.db.commit()
            return self._to_response(categoria)
        except SQLAlchemyError as exc:
            self.repository.db.rollback()
            raise AppException("No se pudo actualizar la categoría", status_code=500) from exc

    def toggle_status(self, id_categoria: int) -> CategoryAdminResponse:
        categoria = self.repository.get_by_id(id_categoria)
        if categoria is None:
            raise AppException("Categoría no encontrada", status_code=404)
        new_status = "INACTIVO" if categoria.estado == "ACTIVO" else "ACTIVO"
        try:
            categoria = self.repository.update(categoria, estado=new_status)
            self.repository.db.commit()
            return self._to_response(categoria)
        except SQLAlchemyError as exc:
            self.repository.db.rollback()
            raise AppException("No se pudo cambiar el estado de la categoría", status_code=500) from exc

    def delete(self, id_categoria: int) -> None:
        categoria = self.repository.get_by_id(id_categoria)
        if categoria is None:
            raise AppException("Categoría no encontrada", status_code=404)
        if self.repository.is_used(id_categoria):
            raise AppException("No se puede eliminar una categoría que ya tiene productos", status_code=409)
        try:
            self.repository.delete(categoria)
            self.repository.db.commit()
        except SQLAlchemyError as exc:
            self.repository.db.rollback()
            raise AppException("No se pudo eliminar la categoría", status_code=500) from exc

    @staticmethod
    def _to_response(categoria: Categoria) -> CategoryAdminResponse:
        return CategoryAdminResponse(
            id_categoria=categoria.id_categoria,
            nombre=categoria.nombre,
            descripcion=categoria.descripcion,
            estado=categoria.estado or "ACTIVO",
        )
