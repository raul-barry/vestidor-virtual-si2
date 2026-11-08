from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class LoyaltyProgram(Base):
    __tablename__ = "loyalty_program"
    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizacion.id_organizacion", ondelete="CASCADE"), nullable=False, index=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False, default="FashionStore Rewards")
    points_per_currency: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=Decimal("1"))
    currency_per_point: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=Decimal("0.01"))
    minimum_redeem_points: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    max_discount_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("20"))
    expiration_days: Mapped[int | None] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("organization_id", name="uq_loyalty_program_org"),
        CheckConstraint("points_per_currency > 0 AND currency_per_point > 0", name="ck_loyalty_rates_positive"),
        CheckConstraint("minimum_redeem_points >= 0 AND (expiration_days IS NULL OR expiration_days > 0)", name="ck_loyalty_program_limits"),
        CheckConstraint("max_discount_percent >= 0 AND max_discount_percent <= 100", name="ck_loyalty_discount_percent"),
    )


class LoyaltyTier(Base):
    __tablename__ = "loyalty_tier"
    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_loyalty_tier_org_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizacion.id_organizacion", ondelete="CASCADE"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    minimum_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class LoyaltyAccount(Base):
    __tablename__ = "loyalty_account"
    __table_args__ = (
        UniqueConstraint("organization_id", "customer_id", name="uq_loyalty_account_org_customer"),
        CheckConstraint("balance >= 0", name="ck_loyalty_balance_nonnegative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizacion.id_organizacion", ondelete="CASCADE"), nullable=False, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("cliente.id_cliente", ondelete="RESTRICT"), nullable=False, index=True)
    balance: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    earned_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    redeemed_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expired_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    customer: Mapped["Cliente"] = relationship()


class LoyaltyLedger(Base):
    __tablename__ = "loyalty_ledger"
    __table_args__ = (
        UniqueConstraint("organization_id", "event_key", name="uq_loyalty_ledger_org_event"),
        CheckConstraint("points <> 0 OR kind IN ('EXPIRACION', 'REVERSO')", name="ck_loyalty_ledger_nonzero"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizacion.id_organizacion", ondelete="CASCADE"), nullable=False, index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("loyalty_account.id", ondelete="RESTRICT"), nullable=False, index=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("pedido.id_pedido", ondelete="SET NULL"), nullable=True, index=True)
    event_key: Mapped[str] = mapped_column(String(180), nullable=False)
    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
