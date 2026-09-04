from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.bitacora import Bitacora
from app.models.cliente import Cliente
from app.models.rol import Rol
from app.models.sesion import Sesion
from app.models.token_recuperacion import TokenRecuperacion
from app.models.usuario import Usuario


class UsuarioRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_user(self, usuario: Usuario) -> Usuario:
        self.db.add(usuario)
        self.db.flush()
        self.db.refresh(usuario)
        return usuario

    def get_by_email(self, correo: str) -> Usuario | None:
        statement = select(Usuario).where(Usuario.correo == correo)
        return self.db.scalar(statement)

    def get_role_by_name(self, nombre: str) -> Rol | None:
        statement = select(Rol).where(Rol.nombre == nombre)
        return self.db.scalar(statement)

    def create_client(self, id_usuario: int) -> Cliente:
        cliente = Cliente(id_usuario=id_usuario)
        self.db.add(cliente)
        self.db.flush()
        self.db.refresh(cliente)
        return cliente

    def create_session(self, sesion: Sesion) -> Sesion:
        self.db.add(sesion)
        self.db.flush()
        self.db.refresh(sesion)
        return sesion

    def create_bitacora(self, bitacora: Bitacora) -> Bitacora:
        self.db.add(bitacora)
        self.db.flush()
        self.db.refresh(bitacora)
        return bitacora

    def get_active_session_by_user(self, id_usuario: int) -> Sesion | None:
        statement = (
            select(Sesion)
            .where(Sesion.id_usuario == id_usuario, Sesion.estado == "ACTIVA")
            .order_by(Sesion.fecha_inicio.desc())
        )
        return self.db.scalar(statement)

    def update_session_status(self, sesion: Sesion, estado: str) -> Sesion:
        sesion.estado = estado
        self.db.flush()
        self.db.refresh(sesion)
        return sesion

    def create_recovery_token(self, token: TokenRecuperacion) -> TokenRecuperacion:
        self.db.add(token)
        self.db.flush()
        self.db.refresh(token)
        return token

    def get_valid_recovery_token(self, token: str, now: datetime) -> TokenRecuperacion | None:
        statement = select(TokenRecuperacion).where(
            TokenRecuperacion.token == token,
            TokenRecuperacion.usado.is_(False),
            TokenRecuperacion.fecha_expiracion > now,
        )
        return self.db.scalar(statement)

    def update_password(self, usuario: Usuario, password_hash: str) -> Usuario:
        usuario.password_hash = password_hash
        self.db.flush()
        self.db.refresh(usuario)
        return usuario

    def mark_token_used(self, token: TokenRecuperacion) -> TokenRecuperacion:
        token.usado = True
        self.db.flush()
        self.db.refresh(token)
        return token

    def get_by_id(self, id_usuario: int) -> Usuario | None:
        return self.db.get(Usuario, id_usuario)

    def get_user_profile(self, id_usuario: int) -> Usuario | None:
        return self.db.get(Usuario, id_usuario)

    def update_user_profile(self, usuario: Usuario, **values: object) -> Usuario:
        for field, value in values.items():
            setattr(usuario, field, value)
        self.db.flush()
        self.db.refresh(usuario)
        return usuario

    def update(self, usuario: Usuario, **values: object) -> Usuario:
        for field, value in values.items():
            if hasattr(usuario, field):
                setattr(usuario, field, value)
        self.db.flush()
        self.db.refresh(usuario)
        return usuario

    # Compatibility aliases for the existing authentication base service.
    def create(self, usuario: Usuario) -> Usuario:
        return self.create_user(usuario)

    def get_by_correo(self, correo: str) -> Usuario | None:
        return self.get_by_email(correo)
