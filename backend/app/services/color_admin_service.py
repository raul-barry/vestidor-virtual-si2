from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.color import Color
from app.repositories.color_admin_repository import ColorRepository
from app.schemas.color_admin import ColorAdminResponse, CreateColorRequest, UpdateColorRequest


class ColorAdminService:
    def __init__(self, db: Session) -> None:
        self.repository = ColorRepository(db)

    def list(self) -> list[ColorAdminResponse]:
        return [self._to_response(c) for c in self.repository.get_all()]

    def get_by_id(self, id_color: int) -> ColorAdminResponse:
        color = self.repository.get_by_id(id_color)
        if color is None:
            raise AppException("Color no encontrado", status_code=404)
        return self._to_response(color)

    def create(self, request: CreateColorRequest) -> ColorAdminResponse:
        if self.repository.get_by_name(request.nombre):
            raise AppException("Ya existe un color con ese nombre", status_code=409)
        try:
            color = self.repository.create(Color(nombre=request.nombre, estado=request.estado or "ACTIVO"))
            self.repository.db.commit()
            return self._to_response(color)
        except SQLAlchemyError as exc:
            self.repository.db.rollback()
            raise AppException("No se pudo crear el color", status_code=500) from exc

    def update(self, id_color: int, request: UpdateColorRequest) -> ColorAdminResponse:
        color = self.repository.get_by_id(id_color)
        if color is None:
            raise AppException("Color no encontrado", status_code=404)
        values = request.model_dump(exclude_none=True)
        if "nombre" in values:
            existing = self.repository.get_by_name(values["nombre"])
            if existing is not None and existing.id_color != id_color:
                raise AppException("Ya existe un color con ese nombre", status_code=409)
        try:
            color = self.repository.update(color, **values)
            self.repository.db.commit()
            return self._to_response(color)
        except SQLAlchemyError as exc:
            self.repository.db.rollback()
            raise AppException("No se pudo actualizar el color", status_code=500) from exc

    def toggle_status(self, id_color: int) -> ColorAdminResponse:
        color = self.repository.get_by_id(id_color)
        if color is None:
            raise AppException("Color no encontrado", status_code=404)
        new_status = "INACTIVO" if color.estado == "ACTIVO" else "ACTIVO"
        try:
            color = self.repository.update(color, estado=new_status)
            self.repository.db.commit()
            return self._to_response(color)
        except SQLAlchemyError as exc:
            self.repository.db.rollback()
            raise AppException("No se pudo cambiar el estado del color", status_code=500) from exc

    def delete(self, id_color: int) -> None:
        color = self.repository.get_by_id(id_color)
        if color is None:
            raise AppException("Color no encontrado", status_code=404)
        if self.repository.is_used(id_color):
            raise AppException("No se puede eliminar un color que ya tiene variantes", status_code=409)
        try:
            self.repository.delete(color)
            self.repository.db.commit()
        except SQLAlchemyError as exc:
            self.repository.db.rollback()
            raise AppException("No se pudo eliminar el color", status_code=500) from exc

    @staticmethod
    def _to_response(color: Color) -> ColorAdminResponse:
        return ColorAdminResponse(id_color=color.id_color, nombre=color.nombre, estado=color.estado or "ACTIVO")

