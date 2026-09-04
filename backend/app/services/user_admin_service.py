from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.usuario import Usuario
from app.repositories.user_admin_repository import UserAdminRepository
from app.schemas.user_admin import UserAdminResponse


class UserAdminService:
    def __init__(self, db: Session) -> None:
        self.repository = UserAdminRepository(db)

    def list_users(self) -> list[UserAdminResponse]:
        return [self._to_response(user) for user in self.repository.get_all_users()]

    def get_user_detail(self, id_usuario: int) -> UserAdminResponse:
        return self._to_response(self._get_user(id_usuario))

    def change_status(self, id_usuario: int, estado: str, admin_id: int) -> UserAdminResponse:
        user = self._get_user(id_usuario)
        new_state = estado.upper()
        current_state = user.estado.upper()
        if (
            user.rol.nombre == "ADMINISTRADOR"
            and current_state == "ACTIVO"
            and new_state == "INACTIVO"
            and self.repository.count_admin_users() <= 1
        ):
            raise AppException("No se puede desactivar el último administrador", status_code=422)

        try:
            self.repository.update_user_status(user, new_state)
            self.repository.create_audit(
                admin_id,
                f"Administrador {admin_id} cambió estado de usuario {user.id_usuario}: {current_state} -> {new_state}",
            )
            self.repository.db.commit()
            return self._to_response(self._get_user(id_usuario))
        except SQLAlchemyError as exc:
            self.repository.db.rollback()
            raise AppException("No se pudo actualizar el estado del usuario", status_code=500) from exc

    def change_role(self, id_usuario: int, id_rol: int, admin_id: int) -> UserAdminResponse:
        if id_usuario == admin_id:
            raise AppException("No se permite cambiar el rol del administrador actual", status_code=422)
        user = self._get_user(id_usuario)
        role = self.repository.get_role_by_id(id_rol)
        if role is None:
            raise AppException("Rol no encontrado", status_code=404)
        if (
            user.rol.nombre == "ADMINISTRADOR"
            and role.nombre != "ADMINISTRADOR"
            and user.estado.upper() == "ACTIVO"
            and self.repository.count_admin_users() <= 1
        ):
            raise AppException("No se puede cambiar el rol del último administrador", status_code=422)

        previous_role = user.rol.nombre
        try:
            self.repository.update_user_role(user, role.id_rol)
            self.repository.create_audit(
                admin_id,
                f"Administrador {admin_id} cambió rol de usuario {user.id_usuario}: {previous_role} -> {role.nombre}",
            )
            self.repository.db.commit()
            return self._to_response(self._get_user(id_usuario))
        except SQLAlchemyError as exc:
            self.repository.db.rollback()
            raise AppException("No se pudo actualizar el rol del usuario", status_code=500) from exc

    def _get_user(self, id_usuario: int) -> Usuario:
        user = self.repository.get_user_by_id(id_usuario)
        if user is None:
            raise AppException("Usuario no encontrado", status_code=404)
        return user

    @staticmethod
    def _to_response(user: Usuario) -> UserAdminResponse:
        return UserAdminResponse(
            id_usuario=user.id_usuario,
            nombres=user.nombres,
            apellidos=user.apellidos,
            correo=user.correo,
            telefono=user.telefono,
            estado=user.estado.upper(),
            rol=user.rol.nombre,
        )
