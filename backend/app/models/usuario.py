from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Usuario(Base):
    __tablename__ = "usuario"

    id_usuario: Mapped[int] = mapped_column(primary_key=True)
    id_sucursal: Mapped[int | None] = mapped_column(ForeignKey("sucursal.id_sucursal"))
    id_rol: Mapped[int] = mapped_column(ForeignKey("rol.id_rol"), nullable=False, index=True)
    nombres: Mapped[str] = mapped_column(String(100), nullable=False)
    apellidos: Mapped[str] = mapped_column(String(100), nullable=False)
    correo: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    telefono: Mapped[str | None] = mapped_column(String(30))
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    estado: Mapped[str] = mapped_column(String(30), nullable=False, default="activo")
    fecha_registro: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    rol: Mapped["Rol"] = relationship(back_populates="usuarios")
    cliente: Mapped["Cliente | None"] = relationship(back_populates="usuario", uselist=False)
    sesiones: Mapped[list["Sesion"]] = relationship(back_populates="usuario")
    tokens_recuperacion: Mapped[list["TokenRecuperacion"]] = relationship(back_populates="usuario")
    bitacoras: Mapped[list["Bitacora"]] = relationship(back_populates="usuario")
