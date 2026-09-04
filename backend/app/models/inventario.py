from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Inventario(Base):
    __tablename__ = "inventario"
    __table_args__ = (UniqueConstraint("id_sucursal", "id_variante"),)

    id_inventario: Mapped[int] = mapped_column(primary_key=True)
    id_sucursal: Mapped[int] = mapped_column(ForeignKey("sucursal.id_sucursal"), nullable=False, index=True)
    id_variante: Mapped[int] = mapped_column(ForeignKey("producto_variante.id_variante"), nullable=False, index=True)
    stock_disponible: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stock_reservado: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    sucursal: Mapped["Sucursal"] = relationship(back_populates="inventarios")
    variante: Mapped["ProductoVariante"] = relationship(back_populates="inventarios")
    movimientos: Mapped[list["MovimientoInventario"]] = relationship(back_populates="inventario")
