from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class CarritoDetalle(Base):
    __tablename__ = "carrito_detalle"
    __table_args__ = (UniqueConstraint("id_carrito", "id_variante"),)

    id_detalle: Mapped[int] = mapped_column(primary_key=True)
    id_carrito: Mapped[int] = mapped_column(ForeignKey("carrito.id_carrito"), nullable=False, index=True)
    id_variante: Mapped[int] = mapped_column(
        ForeignKey("producto_variante.id_variante"), nullable=False, index=True
    )
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    carrito: Mapped["Carrito"] = relationship(back_populates="detalles")
    variante: Mapped["ProductoVariante"] = relationship()
