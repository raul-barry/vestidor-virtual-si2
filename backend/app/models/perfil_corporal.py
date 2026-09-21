from sqlalchemy import Boolean, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class PerfilCorporal(Base):
    __tablename__ = "perfil_corporal"
    id_perfil_corporal: Mapped[int] = mapped_column(primary_key=True)
    id_usuario: Mapped[int] = mapped_column(ForeignKey("usuario.id_usuario"), unique=True, nullable=False, index=True)
    consentimiento: Mapped[bool] = mapped_column(Boolean, nullable=False)
    altura_cm: Mapped[float | None] = mapped_column(Numeric(6, 2))
    peso_kg: Mapped[float | None] = mapped_column(Numeric(6, 2))
    pecho_cm: Mapped[float | None] = mapped_column(Numeric(6, 2))
    cintura_cm: Mapped[float | None] = mapped_column(Numeric(6, 2))
    cadera_cm: Mapped[float | None] = mapped_column(Numeric(6, 2))
    largo_pierna_cm: Mapped[float | None] = mapped_column(Numeric(6, 2))
    ancho_hombros_cm: Mapped[float | None] = mapped_column(Numeric(6, 2))
    foto_frontal: Mapped[str | None] = mapped_column(String(500))
    foto_posterior: Mapped[str | None] = mapped_column(String(500))
    foto_lateral_izquierda: Mapped[str | None] = mapped_column(String(500))
    foto_lateral_derecha: Mapped[str | None] = mapped_column(String(500))
