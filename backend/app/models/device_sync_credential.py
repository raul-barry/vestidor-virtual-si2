from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DeviceSyncCredential(Base):
    __tablename__ = "device_sync_credential"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_device_sync_credential_token_hash"),
        Index("ix_device_sync_credential_org_user", "organizacion_id", "usuario_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organizacion_id: Mapped[int] = mapped_column(ForeignKey("organizacion.id_organizacion", ondelete="CASCADE"), nullable=False)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id_usuario", ondelete="CASCADE"), nullable=False)
    client_id: Mapped[str] = mapped_column(String(100), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
