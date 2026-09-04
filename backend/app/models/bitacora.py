from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Bitacora(Base):
    __tablename__ = "bitacora"

    nro_bitacora: Mapped[int] = mapped_column(primary_key=True)
    id_usuario: Mapped[int] = mapped_column(ForeignKey("usuario.id_usuario"), nullable=False, index=True)
    accion: Mapped[str] = mapped_column(String(255), nullable=False)
    fecha_hora: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    usuario: Mapped["Usuario"] = relationship(back_populates="bitacoras")
