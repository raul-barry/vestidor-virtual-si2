from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PaymentAdjustment(Base):
    __tablename__ = "payment_adjustment"
    __table_args__ = (
        UniqueConstraint("organization_id", "operation_uuid", name="uq_adjustment_org_operation"),
        UniqueConstraint("exchange_id", name="uq_adjustment_exchange"),
        CheckConstraint("amount > 0", name="ck_payment_adjustment_amount"),
        Index("ix_payment_adjustment_org_state", "organization_id", "state"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizacion.id_organizacion", ondelete="RESTRICT"), nullable=False)
    exchange_id: Mapped[int] = mapped_column(ForeignKey("garment_exchange.id", ondelete="RESTRICT"), nullable=False)
    original_payment_id: Mapped[int] = mapped_column(ForeignKey("pago.id_pago", ondelete="RESTRICT"), nullable=False)
    operation_uuid: Mapped[str] = mapped_column(String(36), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDIENTE")
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    provider_reference: Mapped[str | None] = mapped_column(String(255), unique=True)
    provider_event_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    simulated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
