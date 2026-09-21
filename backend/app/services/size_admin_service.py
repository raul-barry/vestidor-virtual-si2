from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.talla import Talla
from app.repositories.size_admin_repository import SizeRepository
from app.schemas.size_admin import SizeAdminResponse, CreateSizeRequest, UpdateSizeRequest


class SizeAdminService:
    def __init__(self, db: Session) -> None:
        self.repository = SizeRepository(db)

    def list(self) -> list[SizeAdminResponse]:
        return [self._to_response(t) for t in self.repository.get_all()]

    def get_by_id(self, id_talla: int) -> SizeAdminResponse:
        talla = self.repository.get_by_id(id_talla)
        if talla is None:
            raise AppException("Talla no encontrada", status_code=404)
        return self._to_response(talla)

    def create(self, request: CreateSizeRequest) -> SizeAdminResponse:
        if self.repository.get_by_name(request.nombre):
            raise AppException("Ya existe una talla con ese nombre", status_code=409)
        try:
            talla = self.repository.create(Talla(nombre=request.nombre, estado=request.estado or "ACTIVO"))
            self.repository.db.commit()
            return self._to_response(talla)
        except SQLAlchemyError as exc:
            self.repository.db.rollback()
            raise AppException("No se pudo crear la talla", status_code=500) from exc

    def update(self, id_talla: int, request: UpdateSizeRequest) -> SizeAdminResponse:
        talla = self.repository.get_by_id(id_talla)
        if talla is None:
            raise AppException("Talla no encontrada", status_code=404)
        values = request.model_dump(exclude_none=True)
        if "nombre" in values:
            existing = self.repository.get_by_name(values["nombre"])
            if existing is not None and existing.id_talla != id_talla:
                raise AppException("Ya existe una talla con ese nombre", status_code=409)
        try:
            talla = self.repository.update(talla, **values)
            self.repository.db.commit()
            return self._to_response(talla)
        except SQLAlchemyError as exc:
            self.repository.db.rollback()
            raise AppException("No se pudo actualizar la talla", status_code=500) from exc

    def toggle_status(self, id_talla: int) -> SizeAdminResponse:
        talla = self.repository.get_by_id(id_talla)
        if talla is None:
            raise AppException("Talla no encontrada", status_code=404)
        new_status = "INACTIVO" if talla.estado == "ACTIVO" else "ACTIVO"
        try:
            talla = self.repository.update(talla, estado=new_status)
            self.repository.db.commit()
            return self._to_response(talla)
        except SQLAlchemyError as exc:
            self.repository.db.rollback()
            raise AppException("No se pudo cambiar el estado de la talla", status_code=500) from exc

    def delete(self, id_talla: int) -> None:
        talla = self.repository.get_by_id(id_talla)
        if talla is None:
            raise AppException("Talla no encontrada", status_code=404)
        if self.repository.is_used(id_talla):
            raise AppException("No se puede eliminar una talla que ya tiene variantes", status_code=409)
        try:
            self.repository.delete(talla)
            self.repository.db.commit()
        except SQLAlchemyError as exc:
            self.repository.db.rollback()
            raise AppException("No se pudo eliminar la talla", status_code=500) from exc

    @staticmethod
    def _to_response(talla: Talla) -> SizeAdminResponse:
        return SizeAdminResponse(id_talla=talla.id_talla, nombre=talla.nombre, estado=talla.estado or "ACTIVO")

