from datetime import datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Plan(Base):
    __tablename__ = "plan"
    __table_args__ = (
        UniqueConstraint("codigo", name="uq_plan_codigo"),
        CheckConstraint("max_sucursales IS NULL OR max_sucursales > 0", name="ck_plan_max_sucursales_positivo"),
    )

    id_plan: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(40), nullable=False)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    max_sucursales: Mapped[int | None] = mapped_column(Integer, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc),
    )

    caracteristicas: Mapped[list["PlanCaracteristica"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan", passive_deletes=True
    )


class PlanCaracteristica(Base):
    __tablename__ = "plan_caracteristica"
    __table_args__ = (
        UniqueConstraint("plan_id", "codigo", name="uq_plan_caracteristica_plan_codigo"),
        CheckConstraint("limite IS NULL OR limite >= 0", name="ck_plan_caracteristica_limite_no_negativo"),
    )

    id_plan_caracteristica: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("plan.id_plan", ondelete="CASCADE"), nullable=False, index=True
    )
    codigo: Mapped[str] = mapped_column(String(80), nullable=False)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    habilitada: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    limite: Mapped[int | None] = mapped_column(Integer, nullable=True)
    configuracion: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    plan: Mapped[Plan] = relationship(back_populates="caracteristicas")
