from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Talla(Base):
    __tablename__ = "talla"

    id_talla: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)

    variantes: Mapped[list["ProductoVariante"]] = relationship(back_populates="talla")
