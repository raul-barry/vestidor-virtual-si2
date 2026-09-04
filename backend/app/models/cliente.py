from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Cliente(Base):
    __tablename__ = "cliente"

    id_cliente: Mapped[int] = mapped_column(primary_key=True)
    id_usuario: Mapped[int] = mapped_column(ForeignKey("usuario.id_usuario"), unique=True, nullable=False)
    fecha_registro: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    estado: Mapped[str] = mapped_column(String(30), nullable=False, default="activo")

    usuario: Mapped["Usuario"] = relationship(back_populates="cliente")
