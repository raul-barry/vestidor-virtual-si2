from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Pedido(Base):
    __tablename__ = "pedido"

    id_pedido: Mapped[int] = mapped_column(primary_key=True)
    id_cliente: Mapped[int] = mapped_column(ForeignKey("cliente.id_cliente"), nullable=False, index=True)
    fecha_pedido: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    estado: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDIENTE")
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    cliente: Mapped["Cliente"] = relationship()
    detalles: Mapped[list["PedidoDetalle"]] = relationship(back_populates="pedido")
