from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Sesion(Base):
    __tablename__ = "sesion"

    id_sesion: Mapped[int] = mapped_column(primary_key=True)
    id_usuario: Mapped[int] = mapped_column(ForeignKey("usuario.id_usuario"), nullable=False, index=True)
    token_jwt: Mapped[str] = mapped_column(String(2048), nullable=False)
    fecha_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fecha_expiracion: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    estado: Mapped[str] = mapped_column(String(30), nullable=False, default="activo")

    usuario: Mapped["Usuario"] = relationship(back_populates="sesiones")
