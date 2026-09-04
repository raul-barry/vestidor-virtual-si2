from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.bitacora import Bitacora
from app.models.usuario import Usuario
from app.repositories.cliente_repository import ClienteRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.user import ProfileUpdateRequest


class UserService:
    def __init__(self, db: Session) -> None:
        self.user_repository = UsuarioRepository(db)
        self.client_repository = ClienteRepository(db)

    def get_profile(self, id_usuario: int) -> Usuario:
        usuario = self.user_repository.get_user_profile(id_usuario)
        if usuario is None:
            raise AppException("Usuario no encontrado", status_code=404)
        if self.client_repository.get_client_by_user(id_usuario) is None:
            raise AppException("Cliente no encontrado", status_code=404)
        return usuario

    def update_profile(self, id_usuario: int, request: ProfileUpdateRequest) -> Usuario:
        usuario = self.get_profile(id_usuario)
        values = request.model_dump(exclude_none=True)

        try:
            usuario = self.user_repository.update_user_profile(usuario, **values)
            self.user_repository.create_bitacora(
                Bitacora(id_usuario=id_usuario, accion="Actualización de perfil")
            )
            self.user_repository.db.commit()
            return usuario
        except SQLAlchemyError as exc:
            self.user_repository.db.rollback()
            raise AppException("No se pudo actualizar el perfil", status_code=500) from exc
