from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Suscripcion(Base):
    __tablename__ = "suscripcion"
    __table_args__ = (
        CheckConstraint(
            "estado IN ('ACTIVA', 'VENCIDA', 'CANCELADA', 'FINALIZADA')",
            name="ck_suscripcion_estado",
        ),
        CheckConstraint(
            "fecha_fin IS NULL OR fecha_fin > fecha_inicio",
            name="ck_suscripcion_fecha_fin_posterior_inicio",
        ),
        Index(
            "uq_suscripcion_organizacion_activa",
            "organizacion_id",
            unique=True,
            postgresql_where=text("estado = 'ACTIVA'"),
            sqlite_where=text("estado = 'ACTIVA'"),
        ),
    )

    id_suscripcion: Mapped[int] = mapped_column(primary_key=True)
    organizacion_id: Mapped[int] = mapped_column(
        ForeignKey("organizacion.id_organizacion", ondelete="RESTRICT"), nullable=False, index=True
    )
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("plan.id_plan", ondelete="RESTRICT"), nullable=False, index=True
    )
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVA")
    fecha_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fecha_fin: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc),
    )
    creado_por_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuario.id_usuario", ondelete="SET NULL"), nullable=True, index=True
    )

    organizacion: Mapped["Organizacion"] = relationship()
    plan: Mapped["Plan"] = relationship()
    creado_por: Mapped["Usuario | None"] = relationship()
