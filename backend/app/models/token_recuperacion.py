from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class TokenRecuperacion(Base):
    __tablename__ = "token_recuperacion"

    id_token: Mapped[int] = mapped_column(primary_key=True)
    id_usuario: Mapped[int] = mapped_column(ForeignKey("usuario.id_usuario"), nullable=False, index=True)
    token: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    fecha_expiracion: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    usado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    usuario: Mapped["Usuario"] = relationship(back_populates="tokens_recuperacion")
