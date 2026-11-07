from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Sucursal(Base):
    __tablename__ = "sucursal"
    __table_args__ = (UniqueConstraint("id_organizacion", "nombre", name="uq_sucursal_organizacion_nombre"),)

    id_sucursal: Mapped[int] = mapped_column(primary_key=True)
    id_organizacion: Mapped[int] = mapped_column(ForeignKey("organizacion.id_organizacion"), nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    direccion: Mapped[str] = mapped_column(String(255), nullable=False)
    ciudad: Mapped[str] = mapped_column(String(100), nullable=False, default="Santa Cruz")
    estado: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVA")

    inventarios: Mapped[list["Inventario"]] = relationship(back_populates="sucursal")
    organizacion: Mapped["Organizacion"] = relationship(back_populates="sucursales")
