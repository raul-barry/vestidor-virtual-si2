import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.exceptions import AppException
from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models.bitacora import Bitacora
from app.models.sesion import Sesion
from app.models.token_recuperacion import TokenRecuperacion
from app.models.usuario import Usuario
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.auth import PasswordResetConfirm, PasswordResetRequest, LoginRequest, RegisterRequest
from app.schemas.usuario import UsuarioCreate


class AuthService:
    def __init__(self, db: Session) -> None:
        self.repository = UsuarioRepository(db)

    def register_usuario(self, usuario_data: UsuarioCreate, id_rol: int) -> Usuario:
        if self.repository.get_by_correo(usuario_data.correo):
            raise AppException("El correo ya se encuentra registrado", status_code=409)

        usuario = Usuario(
            id_rol=id_rol,
            nombres=usuario_data.nombres,
            apellidos=usuario_data.apellidos,
            correo=usuario_data.correo,
            telefono=usuario_data.telefono,
            password_hash=hash_password(usuario_data.password),
        )
        return self.repository.create(usuario)

    def register_client(self, request: RegisterRequest) -> Usuario:
        if self.repository.get_by_email(request.correo):
            raise AppException("El correo ya está registrado", status_code=400)

        client_role = self.repository.get_role_by_name("CLIENTE")
        if client_role is None:
            raise AppException("El rol CLIENTE no está configurado", status_code=500)

        usuario = Usuario(
            id_rol=client_role.id_rol,
            nombres=request.nombres,
            apellidos=request.apellidos,
            correo=request.correo,
            telefono=request.telefono,
            password_hash=hash_password(request.password),
        )

        try:
            usuario = self.repository.create_user(usuario)
            self.repository.create_client(usuario.id_usuario)
            self.repository.db.commit()
            self.repository.db.refresh(usuario)
            return usuario
        except IntegrityError as exc:
            self.repository.db.rollback()
            raise AppException("El correo ya está registrado", status_code=400) from exc
        except SQLAlchemyError as exc:
            self.repository.db.rollback()
            raise AppException("No se pudo registrar el cliente", status_code=500) from exc

    def login_user(self, request: LoginRequest) -> tuple[str, Usuario]:
        usuario = self.repository.get_by_email(request.correo)
        if usuario is None or not verify_password(request.password, usuario.password_hash):
            raise AppException("Credenciales inválidas", status_code=401)
        if usuario.estado.upper() != "ACTIVO":
            raise AppException("Usuario inactivo", status_code=403)

        now = datetime.now(timezone.utc)
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
        token = create_access_token(
            {"id_usuario": usuario.id_usuario, "rol": usuario.rol.nombre},
            expires_delta=expires_delta,
        )

        try:
            self.repository.create_session(
                Sesion(
                    id_usuario=usuario.id_usuario,
                    token_jwt=token,
                    fecha_inicio=now,
                    fecha_expiracion=now + expires_delta,
                    estado="ACTIVA",
                )
            )
            self.repository.create_bitacora(
                Bitacora(id_usuario=usuario.id_usuario, accion="Inicio de sesión", fecha_hora=now)
            )
            self.repository.db.commit()
            return token, usuario
        except SQLAlchemyError as exc:
            self.repository.db.rollback()
            raise AppException("No se pudo iniciar sesión", status_code=500) from exc

    def logout_user(self, usuario: Usuario, token: str | None = None) -> None:
        sesion = self.repository.db.scalar(select(Sesion).where(
            Sesion.id_usuario == usuario.id_usuario, Sesion.token_jwt == token,
            Sesion.estado == "ACTIVA")) if token else self.repository.get_active_session_by_user(usuario.id_usuario)
        if sesion is None:
            raise AppException("Sesión no encontrada", status_code=404)

        try:
            self.repository.update_session_status(sesion, "INACTIVA")
            self.repository.create_bitacora(
                Bitacora(
                    id_usuario=usuario.id_usuario,
                    accion="Cierre de sesión",
                    fecha_hora=datetime.now(timezone.utc),
                )
            )
            self.repository.db.commit()
        except SQLAlchemyError as exc:
            self.repository.db.rollback()
            raise AppException("No se pudo cerrar la sesión", status_code=500) from exc

    def request_password_reset(self, request: PasswordResetRequest) -> str:
        usuario = self.repository.get_by_email(request.correo)
        if usuario is None:
            raise AppException("Usuario no encontrado", status_code=404)

        token_value = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        try:
            self.repository.create_recovery_token(
                TokenRecuperacion(
                    id_usuario=usuario.id_usuario,
                    token=token_value,
                    fecha_expiracion=now
                    + timedelta(minutes=settings.password_reset_token_expire_minutes),
                    usado=False,
                )
            )
            self.repository.create_bitacora(
                Bitacora(
                    id_usuario=usuario.id_usuario,
                    accion="Solicitud de recuperación de contraseña",
                    fecha_hora=now,
                )
            )
            self.repository.db.commit()
            return token_value
        except SQLAlchemyError as exc:
            self.repository.db.rollback()
            raise AppException("No se pudo generar la solicitud de recuperación", status_code=500) from exc

    def reset_password(self, request: PasswordResetConfirm) -> None:
        now = datetime.now(timezone.utc)
        recovery_token = self.repository.get_valid_recovery_token(request.token, now)
        if recovery_token is None:
            raise AppException("Token de recuperación inválido o expirado", status_code=400)

        try:
            self.repository.update_password(recovery_token.usuario, hash_password(request.nueva_password))
            self.repository.mark_token_used(recovery_token)
            for session in self.repository.db.scalars(select(Sesion).where(Sesion.id_usuario == recovery_token.id_usuario)).all():
                session.estado = "INACTIVA"
            for other in self.repository.db.scalars(select(TokenRecuperacion).where(TokenRecuperacion.id_usuario == recovery_token.id_usuario)).all():
                other.usado = True
            self.repository.create_bitacora(
                Bitacora(
                    id_usuario=recovery_token.id_usuario,
                    accion="Restablecimiento de contraseña",
                    fecha_hora=now,
                )
            )
            self.repository.db.commit()
        except SQLAlchemyError as exc:
            self.repository.db.rollback()
            raise AppException("No se pudo actualizar la contraseña", status_code=500) from exc

    def verify_user_password(self, usuario: Usuario, password: str) -> bool:
        return verify_password(password, usuario.password_hash)
