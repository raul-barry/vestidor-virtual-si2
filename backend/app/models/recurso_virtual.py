from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class RecursoVirtual(Base):
    __tablename__ = "recurso_virtual"
    __table_args__ = (
        UniqueConstraint("id_producto", "url_archivo"),
        CheckConstraint("tipo_recurso IN ('imagen', 'modelo_3d')"),
        CheckConstraint("estado IN ('ACTIVO', 'INACTIVO')"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    id_producto: Mapped[int] = mapped_column(ForeignKey("producto.id_producto"), index=True)
    tipo_recurso: Mapped[str] = mapped_column(String(30), default="imagen")
    url_archivo: Mapped[str] = mapped_column(String(500))
    estado: Mapped[str] = mapped_column(String(30), default="ACTIVO")
