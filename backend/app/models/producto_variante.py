from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ProductoVariante(Base):
    __tablename__ = "producto_variante"
    __table_args__ = (UniqueConstraint("id_producto", "id_talla", "id_color"),)

    id_variante: Mapped[int] = mapped_column(primary_key=True)
    id_producto: Mapped[int] = mapped_column(ForeignKey("producto.id_producto"), nullable=False, index=True)
    id_talla: Mapped[int] = mapped_column(ForeignKey("talla.id_talla"), nullable=False, index=True)
    id_color: Mapped[int] = mapped_column(ForeignKey("color.id_color"), nullable=False, index=True)
    sku: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    estado: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVO")

    producto: Mapped["Producto"] = relationship(back_populates="variantes")
    talla: Mapped["Talla"] = relationship(back_populates="variantes")
    color: Mapped["Color"] = relationship(back_populates="variantes")
    inventarios: Mapped[list["Inventario"]] = relationship(back_populates="variante")
