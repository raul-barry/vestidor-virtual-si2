from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.bitacora import Bitacora
from app.models.rol import Rol
from app.models.usuario import Usuario
from app.models.cliente import Cliente


class UserAdminRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all_users(self) -> list[Usuario]:
        statement = select(Usuario).options(joinedload(Usuario.rol)).order_by(Usuario.id_usuario)
        return list(self.db.scalars(statement).all())

    def get_user_by_id(self, id_usuario: int) -> Usuario | None:
        statement = select(Usuario).where(Usuario.id_usuario == id_usuario).options(joinedload(Usuario.rol))
        return self.db.scalar(statement)

    def get_role_by_id(self, id_rol: int) -> Rol | None:
        return self.db.get(Rol, id_rol)

    def get_role_by_name(self, name: str) -> Rol | None:
        return self.db.scalar(select(Rol).where(Rol.nombre == name))

    def create_user(self, user: Usuario) -> Usuario:
        self.db.add(user)
        self.db.flush()
        self.db.refresh(user)
        return user

    def create_client(self, user_id: int) -> Cliente:
        client = Cliente(id_usuario=user_id, estado="ACTIVO")
        self.db.add(client)
        self.db.flush()
        return client

    def update_user_status(self, user: Usuario, estado: str) -> Usuario:
        user.estado = estado
        self.db.flush()
        self.db.refresh(user)
        return user

    def update_user_role(self, user: Usuario, id_rol: int) -> Usuario:
        user.id_rol = id_rol
        self.db.flush()
        self.db.refresh(user)
        return user

    def update_user(self, user: Usuario, **values: object) -> Usuario:
        for field, value in values.items():
            setattr(user, field, value)
        self.db.flush()
        self.db.refresh(user)
        return user

    def count_admin_users(self) -> int:
        statement = (
            select(func.count(Usuario.id_usuario))
            .join(Usuario.rol)
            .where(Rol.nombre == "ADMINISTRADOR", func.upper(Usuario.estado) == "ACTIVO")
        )
        return self.db.scalar(statement) or 0

    def create_audit(self, id_usuario: int, accion: str) -> Bitacora:
        audit = Bitacora(id_usuario=id_usuario, accion=accion)
        self.db.add(audit)
        self.db.flush()
        self.db.refresh(audit)
        return audit
