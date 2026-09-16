from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Sucursal(Base):
    __tablename__ = "sucursal"

    id_sucursal: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    direccion: Mapped[str] = mapped_column(String(255), nullable=False)
    ciudad: Mapped[str] = mapped_column(String(100), nullable=False, default="Santa Cruz")
    estado: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVA")

    inventarios: Mapped[list["Inventario"]] = relationship(back_populates="sucursal")
