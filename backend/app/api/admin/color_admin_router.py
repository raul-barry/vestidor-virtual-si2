from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_admin
from app.database.database import get_db
from app.services.color_admin_service import ColorAdminService
from app.schemas.color_admin import ColorAdminResponse, CreateColorRequest, UpdateColorRequest

color_admin_router = APIRouter(prefix="/admin/colors", tags=["Datos maestros - Colores"])


@color_admin_router.get("", response_model=list[ColorAdminResponse])
def list_colors(db: Session = Depends(get_db), _: object = Depends(get_current_admin)) -> list[ColorAdminResponse]:
    return ColorAdminService(db).list()


@color_admin_router.post("", response_model=ColorAdminResponse, status_code=201)
def create_color(request: CreateColorRequest, db: Session = Depends(get_db), _: object = Depends(get_current_admin)) -> ColorAdminResponse:
    return ColorAdminService(db).create(request)


@color_admin_router.put("/{id_color}", response_model=ColorAdminResponse)
def update_color(id_color: int, request: UpdateColorRequest, db: Session = Depends(get_db), _: object = Depends(get_current_admin)) -> ColorAdminResponse:
    return ColorAdminService(db).update(id_color, request)


@color_admin_router.patch("/{id_color}/toggle-status", response_model=ColorAdminResponse)
def toggle_color_status(id_color: int, db: Session = Depends(get_db), _: object = Depends(get_current_admin)) -> ColorAdminResponse:
    return ColorAdminService(db).toggle_status(id_color)


@color_admin_router.delete("/{id_color}", status_code=204)
def delete_color(id_color: int, db: Session = Depends(get_db), _: object = Depends(get_current_admin)) -> None:
    ColorAdminService(db).delete(id_color)

