from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Color(Base):
    __tablename__ = "color"

    id_color: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    variantes: Mapped[list["ProductoVariante"]] = relationship(back_populates="color")
