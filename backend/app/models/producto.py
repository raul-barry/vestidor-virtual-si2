from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Producto(Base):
    __tablename__ = "producto"

    id_producto: Mapped[int] = mapped_column(primary_key=True)
    id_proveedor: Mapped[int | None] = mapped_column(ForeignKey("proveedor.id_proveedor"))
    id_coleccion: Mapped[int | None] = mapped_column(ForeignKey("coleccion.id_coleccion"))
    id_categoria: Mapped[int] = mapped_column(ForeignKey("categoria.id_categoria"), nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    precio_base: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    estado: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVO")
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    categoria: Mapped["Categoria"] = relationship(back_populates="productos")
    variantes: Mapped[list["ProductoVariante"]] = relationship(back_populates="producto")
