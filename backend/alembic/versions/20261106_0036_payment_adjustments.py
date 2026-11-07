"""Persist exchange price-difference payment operations."""
from alembic import op
import sqlalchemy as sa

revision = "20261106_0036"
down_revision = "20261106_0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payment_adjustment",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizacion.id_organizacion", ondelete="RESTRICT"), nullable=False),
        sa.Column("exchange_id", sa.Integer(), sa.ForeignKey("garment_exchange.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("original_payment_id", sa.Integer(), sa.ForeignKey("pago.id_pago", ondelete="RESTRICT"), nullable=False),
        sa.Column("operation_uuid", sa.String(36), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("state", sa.String(32), nullable=False, server_default="PENDIENTE"),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("provider_reference", sa.String(255), unique=True),
        sa.Column("provider_event_id", sa.String(255), unique=True),
        sa.Column("simulated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("amount > 0", name="ck_payment_adjustment_amount"),
        sa.UniqueConstraint("organization_id", "operation_uuid", name="uq_adjustment_org_operation"),
        sa.UniqueConstraint("exchange_id", name="uq_adjustment_exchange"),
    )
    op.create_index("ix_payment_adjustment_org_state", "payment_adjustment", ["organization_id", "state"])


def downgrade() -> None:
    op.drop_index("ix_payment_adjustment_org_state", table_name="payment_adjustment")
    op.drop_table("payment_adjustment")
