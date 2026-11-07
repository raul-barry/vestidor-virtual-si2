from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PlatformAIConfig(Base):
    """Singleton platform-wide provider configuration; never tenant scoped."""

    __tablename__ = "platform_ai_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    encrypted_api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    models: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    last_test_status: Mapped[str | None] = mapped_column(String(24), nullable=True)
    last_test_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class PlatformAIConfigAudit(Base):
    __tablename__ = "platform_ai_config_audit"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuario.id_usuario", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    result: Mapped[str] = mapped_column(String(24), nullable=False)
    model_ids: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
