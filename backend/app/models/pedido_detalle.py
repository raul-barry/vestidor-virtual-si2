from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class PedidoDetalle(Base):
    __tablename__ = "pedido_detalle"

    id_detalle: Mapped[int] = mapped_column(primary_key=True)
    id_pedido: Mapped[int] = mapped_column(ForeignKey("pedido.id_pedido"), nullable=False, index=True)
    id_variante: Mapped[int] = mapped_column(
        ForeignKey("producto_variante.id_variante"), nullable=False, index=True
    )
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    pedido: Mapped["Pedido"] = relationship(back_populates="detalles")
    variante: Mapped["ProductoVariante"] = relationship()
