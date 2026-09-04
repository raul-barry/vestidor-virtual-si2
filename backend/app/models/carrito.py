from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Carrito(Base):
    __tablename__ = "carrito"

    id_carrito: Mapped[int] = mapped_column(primary_key=True)
    id_cliente: Mapped[int] = mapped_column(ForeignKey("cliente.id_cliente"), unique=True, nullable=False, index=True)
    estado: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVO")
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    cliente: Mapped["Cliente"] = relationship()
    detalles: Mapped[list["CarritoDetalle"]] = relationship(back_populates="carrito")
