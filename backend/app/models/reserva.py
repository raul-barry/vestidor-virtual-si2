from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Reserva(Base):
    __tablename__ = "reserva"
    __table_args__ = (CheckConstraint("cantidad > 0", name="ck_reserva_cantidad"),)

    id_reserva: Mapped[int] = mapped_column(primary_key=True)
    id_usuario: Mapped[int] = mapped_column(ForeignKey("usuario.id_usuario"), index=True)
    id_inventario: Mapped[int] = mapped_column(ForeignKey("inventario.id_inventario"), index=True)
    cantidad: Mapped[int]
    estado: Mapped[str] = mapped_column(String(30), default="PENDIENTE")
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
