from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class MovimientoInventario(Base):
    __tablename__ = "movimiento_inventario"

    id_movimiento: Mapped[int] = mapped_column(primary_key=True)
    id_inventario: Mapped[int] = mapped_column(ForeignKey("inventario.id_inventario"), nullable=False, index=True)
    tipo_movimiento: Mapped[str] = mapped_column(String(20), nullable=False)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    stock_anterior: Mapped[int] = mapped_column(Integer, nullable=False)
    stock_nuevo: Mapped[int] = mapped_column(Integer, nullable=False)
    motivo: Mapped[str] = mapped_column(String(255), nullable=False)
    fecha_movimiento: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    id_usuario: Mapped[int] = mapped_column(ForeignKey("usuario.id_usuario"), nullable=False, index=True)

    inventario: Mapped["Inventario"] = relationship(back_populates="movimientos")
    usuario: Mapped["Usuario"] = relationship()
