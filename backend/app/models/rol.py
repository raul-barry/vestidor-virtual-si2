from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Rol(Base):
    __tablename__ = "rol"

    id_rol: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(255))
    estado: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVO")

    usuarios: Mapped[list["Usuario"]] = relationship(back_populates="rol")
    permisos: Mapped[list["Permiso"]] = relationship(secondary="rol_permiso", back_populates="roles")


class Permiso(Base):
    __tablename__ = "permiso"
    id_permiso: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(255))
    roles: Mapped[list["Rol"]] = relationship(secondary="rol_permiso", back_populates="permisos")


class RolPermiso(Base):
    __tablename__ = "rol_permiso"
    id_rol: Mapped[int] = mapped_column(ForeignKey("rol.id_rol"), primary_key=True)
    id_permiso: Mapped[int] = mapped_column(ForeignKey("permiso.id_permiso"), primary_key=True)
