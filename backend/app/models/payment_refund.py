from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PaymentRefund(Base):
    __tablename__ = "payment_refund"
    __table_args__ = (
        UniqueConstraint("organization_id", "operation_uuid", name="uq_refund_org_operation"),
        UniqueConstraint("organization_id", "exchange_id", name="uq_refund_org_exchange"),
        UniqueConstraint("organization_id", "return_id", name="uq_refund_org_return"),
        CheckConstraint("amount > 0", name="ck_payment_refund_amount"),
        Index("ix_payment_refund_org_state", "organization_id", "state"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizacion.id_organizacion", ondelete="RESTRICT"), nullable=False
    )
    payment_id: Mapped[int] = mapped_column(ForeignKey("pago.id_pago", ondelete="RESTRICT"), nullable=False)
    order_id: Mapped[int] = mapped_column(ForeignKey("pedido.id_pedido", ondelete="RESTRICT"), nullable=False)
    exchange_id: Mapped[int | None] = mapped_column(ForeignKey("garment_exchange.id", ondelete="RESTRICT"))
    return_id: Mapped[int | None] = mapped_column(ForeignKey("devolucion.id_devolucion", ondelete="RESTRICT"))
    requested_by: Mapped[int] = mapped_column(ForeignKey("usuario.id_usuario", ondelete="RESTRICT"), nullable=False)
    operation_uuid: Mapped[str] = mapped_column(String(36), nullable=False)
    method: Mapped[str] = mapped_column(String(30), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="BOB")
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="DEVOLUCION_PENDIENTE")
    provider: Mapped[str | None] = mapped_column(String(40))
    provider_reference: Mapped[str | None] = mapped_column(String(255))
    provider_event_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    evidence_reference: Mapped[str | None] = mapped_column(String(255))
    simulated: Mapped[bool] = mapped_column(default=False, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
