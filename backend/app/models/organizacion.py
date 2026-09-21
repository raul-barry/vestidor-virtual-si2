from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class Organizacion(Base):
    __tablename__ = "organizacion"
    id_organizacion: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    estado: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVA")
