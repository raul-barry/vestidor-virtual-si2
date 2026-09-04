from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.cliente import Cliente


class ClienteRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_client_by_user(self, id_usuario: int) -> Cliente | None:
        statement = select(Cliente).where(Cliente.id_usuario == id_usuario)
        return self.db.scalar(statement)

    def update_client(self, cliente: Cliente, **values: object) -> Cliente:
        for field, value in values.items():
            setattr(cliente, field, value)
        self.db.flush()
        self.db.refresh(cliente)
        return cliente
