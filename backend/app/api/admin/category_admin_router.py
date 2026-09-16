from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_admin
from app.database.database import get_db
from app.services.category_admin_service import CategoryAdminService
from app.schemas.category_admin import CategoryAdminResponse, CreateCategoryRequest, UpdateCategoryRequest

category_admin_router = APIRouter(prefix="/admin/categories", tags=["Datos maestros - Categorías"])


@category_admin_router.get("", response_model=list[CategoryAdminResponse])
def list_categories(db: Session = Depends(get_db), _: object = Depends(get_current_admin)) -> list[CategoryAdminResponse]:
    return CategoryAdminService(db).list()


@category_admin_router.post("", response_model=CategoryAdminResponse, status_code=201)
def create_category(request: CreateCategoryRequest, db: Session = Depends(get_db), _: object = Depends(get_current_admin)) -> CategoryAdminResponse:
    return CategoryAdminService(db).create(request)


@category_admin_router.put("/{id_categoria}", response_model=CategoryAdminResponse)
def update_category(id_categoria: int, request: UpdateCategoryRequest, db: Session = Depends(get_db), _: object = Depends(get_current_admin)) -> CategoryAdminResponse:
    return CategoryAdminService(db).update(id_categoria, request)


@category_admin_router.patch("/{id_categoria}/toggle-status", response_model=CategoryAdminResponse)
def toggle_category_status(id_categoria: int, db: Session = Depends(get_db), _: object = Depends(get_current_admin)) -> CategoryAdminResponse:
    return CategoryAdminService(db).toggle_status(id_categoria)


@category_admin_router.delete("/{id_categoria}", status_code=204)
def delete_category(id_categoria: int, db: Session = Depends(get_db), _: object = Depends(get_current_admin)) -> None:
    CategoryAdminService(db).delete(id_categoria)

