from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class PreferenciaCliente(Base):
    __tablename__ = "preferencia_cliente"
    id_preferencia: Mapped[int] = mapped_column(primary_key=True)
    id_cliente: Mapped[int] = mapped_column(ForeignKey("cliente.id_cliente"), unique=True, nullable=False, index=True)
    talla_superior: Mapped[str | None] = mapped_column(String(50))
    talla_pantalon: Mapped[str | None] = mapped_column(String(50))
    talla_calzado: Mapped[str | None] = mapped_column(String(50))
    estilos: Mapped[str] = mapped_column(String(500), nullable=False, default="")

class PreferenciaClienteColor(Base):
    __tablename__ = "preferencia_cliente_color"
    id_preferencia: Mapped[int] = mapped_column(ForeignKey("preferencia_cliente.id_preferencia"), primary_key=True)
    id_color: Mapped[int] = mapped_column(ForeignKey("color.id_color"), primary_key=True)
