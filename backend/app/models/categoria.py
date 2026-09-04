from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Categoria(Base):
    __tablename__ = "categoria"

    id_categoria: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(255))

    productos: Mapped[list["Producto"]] = relationship(back_populates="categoria")
