from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_admin
from app.database.database import get_db
from app.services.branch_admin_service import BranchAdminService
from app.schemas.branch_admin import BranchAdminResponse, CreateBranchRequest, UpdateBranchRequest

branch_admin_router = APIRouter(prefix="/admin/branches", tags=["Datos maestros - Sucursales"])


@branch_admin_router.get("", response_model=list[BranchAdminResponse])
def list_branches(db: Session = Depends(get_db), _: object = Depends(get_current_admin)) -> list[BranchAdminResponse]:
    return BranchAdminService(db).list()


@branch_admin_router.post("", response_model=BranchAdminResponse, status_code=201)
def create_branch(request: CreateBranchRequest, db: Session = Depends(get_db), _: object = Depends(get_current_admin)) -> BranchAdminResponse:
    return BranchAdminService(db).create(request)


@branch_admin_router.put("/{id_sucursal}", response_model=BranchAdminResponse)
def update_branch(id_sucursal: int, request: UpdateBranchRequest, db: Session = Depends(get_db), _: object = Depends(get_current_admin)) -> BranchAdminResponse:
    return BranchAdminService(db).update(id_sucursal, request)


@branch_admin_router.patch("/{id_sucursal}/toggle-status", response_model=BranchAdminResponse)
def toggle_branch_status(id_sucursal: int, db: Session = Depends(get_db), _: object = Depends(get_current_admin)) -> BranchAdminResponse:
    return BranchAdminService(db).toggle_status(id_sucursal)


@branch_admin_router.delete("/{id_sucursal}", status_code=204)
def delete_branch(id_sucursal: int, db: Session = Depends(get_db), _: object = Depends(get_current_admin)) -> None:
    BranchAdminService(db).delete(id_sucursal)

