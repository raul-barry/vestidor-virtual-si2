from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Organizacion(Base):
    __tablename__ = "organizacion"
    __table_args__ = (
        UniqueConstraint("nombre", name="uq_organizacion_nombre"),
        UniqueConstraint("slug", name="uq_organizacion_slug"),
        Index("uq_organizacion_nit", "nit", unique=True),
    )
    id_organizacion: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    slug: Mapped[str] = mapped_column(String(160), nullable=False)
    estado: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVA")
    razon_social: Mapped[str | None] = mapped_column(String(200), nullable=True)
    nit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    correo_contacto: Mapped[str | None] = mapped_column(String(254), nullable=True)
    telefono_contacto: Mapped[str | None] = mapped_column(String(30), nullable=True)
    direccion: Mapped[str | None] = mapped_column(String(255), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    fecha_creacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=lambda: datetime.now(timezone.utc)
    )
    fecha_actualizacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    usuarios: Mapped[list["Usuario"]] = relationship(back_populates="organizacion")
    sucursales: Mapped[list["Sucursal"]] = relationship(back_populates="organizacion")
    productos: Mapped[list["Producto"]] = relationship(back_populates="organizacion")
    proveedores: Mapped[list["Proveedor"]] = relationship(back_populates="organizacion")
    colecciones: Mapped[list["Coleccion"]] = relationship(back_populates="organizacion")
