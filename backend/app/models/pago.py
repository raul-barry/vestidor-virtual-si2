from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Pago(Base):
    __tablename__ = "pago"

    id_pago: Mapped[int] = mapped_column(primary_key=True)
    id_pedido: Mapped[int] = mapped_column(ForeignKey("pedido.id_pedido"), unique=True, nullable=False, index=True)
    metodo_pago: Mapped[str] = mapped_column(String(30), nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    fecha_pago: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    estado: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDIENTE")

    pedido: Mapped["Pedido"] = relationship()
