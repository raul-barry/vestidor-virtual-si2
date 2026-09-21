from datetime import datetime, date, timezone
from decimal import Decimal
from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class Ciudad(Base):
    __tablename__ = "ciudad"
    id_ciudad: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True)
    descripcion: Mapped[str] = mapped_column(String(255), default="")
    estado: Mapped[str] = mapped_column(String(30), default="ACTIVO")


class Proveedor(Base):
    __tablename__ = "proveedor"
    id_proveedor: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(150), unique=True)
    contacto: Mapped[str] = mapped_column(String(255), default="")
    descripcion: Mapped[str] = mapped_column(String(500), default="")
    persona_contacto: Mapped[str] = mapped_column(String(150), default="")
    telefono: Mapped[str] = mapped_column(String(30), default="")
    correo: Mapped[str] = mapped_column(String(255), default="")
    direccion: Mapped[str] = mapped_column(String(255), default="")
    estado: Mapped[str] = mapped_column(String(30), default="ACTIVO")


class Coleccion(Base):
    __tablename__ = "coleccion"
    id_coleccion: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(150), unique=True)
    descripcion: Mapped[str] = mapped_column(String(255), default="")
    temporada: Mapped[str] = mapped_column(String(80), default="")
    anio: Mapped[int | None]
    fecha_inicio: Mapped[date | None] = mapped_column(Date)
    fecha_fin: Mapped[date | None] = mapped_column(Date)
    estado: Mapped[str] = mapped_column(String(30), default="ACTIVO")


class Promocion(Base):
    __tablename__ = "promocion"
    __table_args__ = (CheckConstraint("descuento > 0 AND descuento <= 100", name="ck_promocion_descuento"),)
    id_promocion: Mapped[int] = mapped_column(primary_key=True)
    id_producto: Mapped[int] = mapped_column(ForeignKey("producto.id_producto"), index=True)
    nombre: Mapped[str] = mapped_column(String(150))
    descuento: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    inicio: Mapped[date] = mapped_column(Date)
    fin: Mapped[date] = mapped_column(Date)
    estado: Mapped[str] = mapped_column(String(30), default="ACTIVO")


class Devolucion(Base):
    __tablename__ = "devolucion"
    __table_args__ = (CheckConstraint("cantidad > 0", name="ck_devolucion_cantidad"),)
    id_devolucion: Mapped[int] = mapped_column(primary_key=True)
    id_detalle: Mapped[int] = mapped_column(ForeignKey("pedido_detalle.id_detalle"), index=True)
    id_inventario: Mapped[int] = mapped_column(ForeignKey("inventario.id_inventario"))
    id_usuario: Mapped[int] = mapped_column(ForeignKey("usuario.id_usuario"))
    cantidad: Mapped[int]
    motivo: Mapped[str] = mapped_column(String(255))
    estado: Mapped[str] = mapped_column(String(30), default="COMPLETADA")
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
