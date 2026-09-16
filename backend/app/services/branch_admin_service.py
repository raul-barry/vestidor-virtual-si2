from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.sucursal import Sucursal
from app.models.comercio import Ciudad
from sqlalchemy import select
from app.repositories.branch_admin_repository import BranchRepository
from app.schemas.branch_admin import BranchAdminResponse, CreateBranchRequest, UpdateBranchRequest


class BranchAdminService:
    def __init__(self, db: Session) -> None:
        self.repository = BranchRepository(db)

    def list(self) -> list[BranchAdminResponse]:
        return [self._to_response(s) for s in self.repository.get_all()]

    def get_by_id(self, id_sucursal: int) -> BranchAdminResponse:
        sucursal = self.repository.get_by_id(id_sucursal)
        if sucursal is None:
            raise AppException("Sucursal no encontrada", status_code=404)
        return self._to_response(sucursal)

    def create(self, request: CreateBranchRequest) -> BranchAdminResponse:
        if self.repository.get_by_name(request.nombre):
            raise AppException("Ya existe una sucursal con ese nombre", status_code=409)
        try:
            self._ensure_city(request.ciudad or "Santa Cruz")
            sucursal = self.repository.create(Sucursal(
                nombre=request.nombre,
                direccion=request.direccion,
                ciudad=request.ciudad or "Santa Cruz",
                estado="ACTIVA",
            ))
            self.repository.db.commit()
            return self._to_response(sucursal)
        except SQLAlchemyError as exc:
            self.repository.db.rollback()
            raise AppException("No se pudo crear la sucursal", status_code=500) from exc

    def update(self, id_sucursal: int, request: UpdateBranchRequest) -> BranchAdminResponse:
        sucursal = self.repository.get_by_id(id_sucursal)
        if sucursal is None:
            raise AppException("Sucursal no encontrada", status_code=404)
        values = request.model_dump(exclude_none=True)
        if "nombre" in values:
            existing = self.repository.get_by_name(values["nombre"])
            if existing is not None and existing.id_sucursal != id_sucursal:
                raise AppException("Ya existe una sucursal con ese nombre", status_code=409)
        try:
            if "ciudad" in values:
                self._ensure_city(values["ciudad"])
            sucursal = self.repository.update(sucursal, **values)
            self.repository.db.commit()
            return self._to_response(sucursal)
        except SQLAlchemyError as exc:
            self.repository.db.rollback()
            raise AppException("No se pudo actualizar la sucursal", status_code=500) from exc

    def toggle_status(self, id_sucursal: int) -> BranchAdminResponse:
        sucursal = self.repository.get_by_id(id_sucursal)
        if sucursal is None:
            raise AppException("Sucursal no encontrada", status_code=404)
        new_status = "INACTIVA" if sucursal.estado == "ACTIVA" else "ACTIVA"
        try:
            sucursal = self.repository.update(sucursal, estado=new_status)
            self.repository.db.commit()
            return self._to_response(sucursal)
        except SQLAlchemyError as exc:
            self.repository.db.rollback()
            raise AppException("No se pudo cambiar el estado de la sucursal", status_code=500) from exc

    def delete(self, id_sucursal: int) -> None:
        sucursal = self.repository.get_by_id(id_sucursal)
        if sucursal is None:
            raise AppException("Sucursal no encontrada", status_code=404)
        if self.repository.is_used(id_sucursal):
            raise AppException("No se puede eliminar una sucursal que ya tiene inventario", status_code=409)
        try:
            self.repository.delete(sucursal)
            self.repository.db.commit()
        except SQLAlchemyError as exc:
            self.repository.db.rollback()
            raise AppException("No se pudo eliminar la sucursal", status_code=500) from exc

    @staticmethod
    def _to_response(sucursal: Sucursal) -> BranchAdminResponse:
        return BranchAdminResponse(
            id_sucursal=sucursal.id_sucursal,
            nombre=sucursal.nombre,
            direccion=sucursal.direccion,
            ciudad=sucursal.ciudad,
            estado=sucursal.estado,
        )

    def _ensure_city(self, name: str) -> None:
        if not name.strip() or len(name) > 100:
            raise AppException("Ciudad inválida", status_code=422)
        city = self.repository.db.scalar(select(Ciudad).where(Ciudad.nombre == name))
        if city is None:
            self.repository.db.add(Ciudad(nombre=name))
            self.repository.db.flush()
        elif city.estado != "ACTIVO":
            raise AppException("Ciudad inactiva", status_code=422)
