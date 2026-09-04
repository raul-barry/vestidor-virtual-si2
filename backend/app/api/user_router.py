from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database.database import get_db
from app.models.usuario import Usuario
from app.schemas.user import ProfileResponse, ProfileUpdateRequest
from app.services.user_service import UserService

user_router = APIRouter(prefix="/users", tags=["Usuarios"])


@user_router.get(
    "/profile",
    response_model=ProfileResponse,
    responses={401: {"description": "Token inválido"}, 404: {"description": "Usuario o cliente no encontrado"}},
)
def get_profile(
    db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)
) -> ProfileResponse:
    usuario = UserService(db).get_profile(current_user.id_usuario)
    return ProfileResponse(
        id_usuario=usuario.id_usuario,
        nombres=usuario.nombres,
        apellidos=usuario.apellidos,
        correo=usuario.correo,
        telefono=usuario.telefono,
    )


@user_router.put(
    "/profile",
    response_model=ProfileResponse,
    responses={
        401: {"description": "Token inválido"},
        404: {"description": "Usuario o cliente no encontrado"},
        500: {"description": "No se pudo actualizar el perfil"},
    },
)
def update_profile(
    request: ProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> ProfileResponse:
    usuario = UserService(db).update_profile(current_user.id_usuario, request)
    return ProfileResponse(
        id_usuario=usuario.id_usuario,
        nombres=usuario.nombres,
        apellidos=usuario.apellidos,
        correo=usuario.correo,
        telefono=usuario.telefono,
    )
