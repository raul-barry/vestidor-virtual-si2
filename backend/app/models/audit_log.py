from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_log_org_fecha", "organizacion_id", "fecha_hora"),
        Index("ix_audit_log_org_accion", "organizacion_id", "accion"),
        Index("ix_audit_log_org_usuario", "organizacion_id", "usuario_id"),
        Index("uq_audit_log_dedupe_key", "dedupe_key", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organizacion_id: Mapped[int] = mapped_column(ForeignKey("organizacion.id_organizacion", ondelete="RESTRICT"), nullable=False)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id_usuario", ondelete="SET NULL"), nullable=True)
    rol: Mapped[str] = mapped_column(String(40), nullable=False)
    accion: Mapped[str] = mapped_column(String(80), nullable=False)
    entidad: Mapped[str] = mapped_column(String(80), nullable=False)
    entidad_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    resultado: Mapped[str] = mapped_column(String(30), nullable=False, default="EXITOSO")
    detalles: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    dedupe_key: Mapped[str | None] = mapped_column(String(160), nullable=True)
