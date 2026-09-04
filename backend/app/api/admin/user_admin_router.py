from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_admin
from app.database.database import get_db
from app.models.usuario import Usuario
from app.schemas.user_admin import UpdateRoleRequest, UpdateStatusRequest, UserAdminResponse
from app.services.user_admin_service import UserAdminService

user_admin_router = APIRouter(prefix="/admin/users", tags=["Administración de usuarios"])


@user_admin_router.get("", response_model=list[UserAdminResponse])
def list_users(
    db: Session = Depends(get_db), _: Usuario = Depends(get_current_admin)
) -> list[UserAdminResponse]:
    return UserAdminService(db).list_users()


@user_admin_router.get("/{id_usuario}", response_model=UserAdminResponse)
def get_user_detail(
    id_usuario: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_admin),
) -> UserAdminResponse:
    return UserAdminService(db).get_user_detail(id_usuario)


@user_admin_router.put("/{id_usuario}/status", response_model=UserAdminResponse)
def change_status(
    id_usuario: int,
    request: UpdateStatusRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_admin),
) -> UserAdminResponse:
    return UserAdminService(db).change_status(id_usuario, request.estado, current_user.id_usuario)


@user_admin_router.put("/{id_usuario}/role", response_model=UserAdminResponse)
def change_role(
    id_usuario: int,
    request: UpdateRoleRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_admin),
) -> UserAdminResponse:
    return UserAdminService(db).change_role(id_usuario, request.id_rol, current_user.id_usuario)
