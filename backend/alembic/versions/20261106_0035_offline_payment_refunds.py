"""Add idempotent payment metadata and monetary refund tracking."""
from alembic import op
import sqlalchemy as sa

revision = "20261106_0035"
down_revision = "20261105_0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pago", sa.Column("idempotency_key", sa.String(36), nullable=True))
    op.create_unique_constraint("uq_pago_idempotency_key", "pago", ["idempotency_key"])
    op.add_column("pago", sa.Column("currency", sa.String(3), nullable=False, server_default="BOB"))
    op.add_column("pago", sa.Column("simulated", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("pago", sa.Column("cash_received", sa.Numeric(12, 2), nullable=True))
    op.add_column("pago", sa.Column("cash_change", sa.Numeric(12, 2), nullable=False, server_default="0"))
    op.create_table(
        "payment_refund",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizacion.id_organizacion", ondelete="RESTRICT"), nullable=False),
        sa.Column("payment_id", sa.Integer(), sa.ForeignKey("pago.id_pago", ondelete="RESTRICT"), nullable=False),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("pedido.id_pedido", ondelete="RESTRICT"), nullable=False),
        sa.Column("exchange_id", sa.Integer(), sa.ForeignKey("garment_exchange.id", ondelete="RESTRICT")),
        sa.Column("return_id", sa.Integer(), sa.ForeignKey("devolucion.id_devolucion", ondelete="RESTRICT")),
        sa.Column("requested_by", sa.Integer(), sa.ForeignKey("usuario.id_usuario", ondelete="RESTRICT"), nullable=False),
        sa.Column("operation_uuid", sa.String(36), nullable=False),
        sa.Column("method", sa.String(30), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="BOB"),
        sa.Column("state", sa.String(32), nullable=False, server_default="DEVOLUCION_PENDIENTE"),
        sa.Column("provider", sa.String(40)),
        sa.Column("provider_reference", sa.String(255)),
        sa.Column("provider_event_id", sa.String(255), unique=True),
        sa.Column("reason", sa.String(255), nullable=False),
        sa.Column("evidence_reference", sa.String(255)),
        sa.Column("simulated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("amount > 0", name="ck_payment_refund_amount"),
        sa.UniqueConstraint("organization_id", "operation_uuid", name="uq_refund_org_operation"),
        sa.UniqueConstraint("organization_id", "exchange_id", name="uq_refund_org_exchange"),
        sa.UniqueConstraint("organization_id", "return_id", name="uq_refund_org_return"),
    )
    op.create_index("ix_payment_refund_org_state", "payment_refund", ["organization_id", "state"])
    op.create_index("ix_payment_refund_order_id", "payment_refund", ["order_id"])
    op.create_index("ix_payment_refund_payment_id", "payment_refund", ["payment_id"])


def downgrade() -> None:
    op.drop_index("ix_payment_refund_payment_id", table_name="payment_refund")
    op.drop_index("ix_payment_refund_order_id", table_name="payment_refund")
    op.drop_index("ix_payment_refund_org_state", table_name="payment_refund")
    op.drop_table("payment_refund")
    op.drop_column("pago", "cash_change")
    op.drop_column("pago", "cash_received")
    op.drop_column("pago", "simulated")
    op.drop_column("pago", "currency")
    op.drop_constraint("uq_pago_idempotency_key", "pago", type_="unique")
    op.drop_column("pago", "idempotency_key")
