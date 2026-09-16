from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_current_user
from app.core.security import bearer_scheme
from fastapi.security import HTTPAuthorizationCredentials
from app.database.database import get_db
from app.models.usuario import Usuario
from app.schemas.auth import (
    AuthenticatedUserResponse,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    PasswordResetResponse,
    RegisterRequest,
    RegisterResponse,
)
from app.services.auth_service import AuthService

auth_router = APIRouter(prefix="/auth", tags=["Autenticacion"])


@auth_router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "El correo ya está registrado"},
        500: {"description": "El rol CLIENTE no está configurado o el registro falló"},
    },
)
def register_client(request: RegisterRequest, db: Session = Depends(get_db)) -> RegisterResponse:
    usuario = AuthService(db).register_client(request)
    return RegisterResponse(
        id_usuario=usuario.id_usuario,
        nombres=usuario.nombres,
        apellidos=usuario.apellidos,
        correo=usuario.correo,
        telefono=usuario.telefono,
        rol=usuario.rol.nombre,
    )


@auth_router.post(
    "/login",
    response_model=LoginResponse,
    responses={
        401: {"description": "Credenciales inválidas"},
        403: {"description": "Usuario inactivo"},
        500: {"description": "No se pudo iniciar sesión"},
    },
)
def login(request: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    token, usuario = AuthService(db).login_user(request)
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        usuario=AuthenticatedUserResponse(id_usuario=usuario.id_usuario, correo=usuario.correo),
        rol=usuario.rol.nombre,
    )


@auth_router.post(
    "/logout",
    response_model=LogoutResponse,
    responses={
        401: {"description": "Token inválido"},
        404: {"description": "Sesión no encontrada"},
        500: {"description": "No se pudo cerrar la sesión"},
    },
)
def logout(
    db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> LogoutResponse:
    AuthService(db).logout_user(current_user, credentials.credentials)
    return LogoutResponse(message="Sesión cerrada correctamente")


@auth_router.post(
    "/request-password-reset",
    response_model=PasswordResetResponse,
    response_model_exclude_none=True,
    responses={
        404: {"description": "Usuario no encontrado"},
        500: {"description": "No se pudo generar la solicitud de recuperación"},
    },
)
def request_password_reset(
    request: PasswordResetRequest, db: Session = Depends(get_db)
) -> PasswordResetResponse:
    token = AuthService(db).request_password_reset(request)
    return PasswordResetResponse(
        message="Solicitud de recuperación generada correctamente",
        token=token if settings.expose_reset_token and settings.environment in ("development", "test") else None,
    )


@auth_router.post(
    "/reset-password",
    response_model=PasswordResetResponse,
    response_model_exclude_none=True,
    responses={
        400: {"description": "Token de recuperación inválido o expirado"},
        500: {"description": "No se pudo actualizar la contraseña"},
    },
)
def reset_password(request: PasswordResetConfirm, db: Session = Depends(get_db)) -> PasswordResetResponse:
    AuthService(db).reset_password(request)
    return PasswordResetResponse(message="Contraseña actualizada correctamente")
