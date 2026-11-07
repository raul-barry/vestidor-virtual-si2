from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SyncIdempotency(Base):
    __tablename__ = "sync_idempotency"
    __table_args__ = (
        UniqueConstraint("organizacion_id", "operation_uuid", name="uq_sync_org_operation_uuid"),
        Index("ix_sync_org_status", "organizacion_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organizacion_id: Mapped[int] = mapped_column(
        ForeignKey("organizacion.id_organizacion", ondelete="RESTRICT"), nullable=False
    )
    operation_uuid: Mapped[str] = mapped_column(String(36), nullable=False)
    operation_type: Mapped[str] = mapped_column(String(80), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    client_id: Mapped[str] = mapped_column(String(100), nullable=False)
    tenant_scope: Mapped[str] = mapped_column(String(180), nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    operation_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    result_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(60), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
