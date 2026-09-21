from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_admin
from app.database.database import get_db
from app.services.size_admin_service import SizeAdminService
from app.schemas.size_admin import SizeAdminResponse, CreateSizeRequest, UpdateSizeRequest

size_admin_router = APIRouter(prefix="/admin/sizes", tags=["Datos maestros - Tallas"])


@size_admin_router.get("", response_model=list[SizeAdminResponse])
def list_sizes(db: Session = Depends(get_db), _: object = Depends(get_current_admin)) -> list[SizeAdminResponse]:
    return SizeAdminService(db).list()


@size_admin_router.post("", response_model=SizeAdminResponse, status_code=201)
def create_size(request: CreateSizeRequest, db: Session = Depends(get_db), _: object = Depends(get_current_admin)) -> SizeAdminResponse:
    return SizeAdminService(db).create(request)


@size_admin_router.put("/{id_talla}", response_model=SizeAdminResponse)
def update_size(id_talla: int, request: UpdateSizeRequest, db: Session = Depends(get_db), _: object = Depends(get_current_admin)) -> SizeAdminResponse:
    return SizeAdminService(db).update(id_talla, request)


@size_admin_router.patch("/{id_talla}/toggle-status", response_model=SizeAdminResponse)
def toggle_size_status(id_talla: int, db: Session = Depends(get_db), _: object = Depends(get_current_admin)) -> SizeAdminResponse:
    return SizeAdminService(db).toggle_status(id_talla)


@size_admin_router.delete("/{id_talla}", status_code=204)
def delete_size(id_talla: int, db: Session = Depends(get_db), _: object = Depends(get_current_admin)) -> None:
    SizeAdminService(db).delete(id_talla)

