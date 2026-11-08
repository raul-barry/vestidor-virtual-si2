"""Add tenant scoped customer loyalty program and ledger."""
from alembic import op
import sqlalchemy as sa

revision = "20261107_0039"
down_revision = "20261106_0038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "loyalty_program",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizacion.id_organizacion", ondelete="CASCADE"), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("name", sa.String(120), nullable=False, server_default="FashionStore Rewards"),
        sa.Column("points_per_currency", sa.Numeric(10, 4), nullable=False, server_default="1"),
        sa.Column("currency_per_point", sa.Numeric(10, 4), nullable=False, server_default="0.01"),
        sa.Column("minimum_redeem_points", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("max_discount_percent", sa.Numeric(5, 2), nullable=False, server_default="20"),
        sa.Column("expiration_days", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", name="uq_loyalty_program_org"),
        sa.CheckConstraint("points_per_currency > 0 AND currency_per_point > 0", name="ck_loyalty_rates_positive"),
        sa.CheckConstraint("minimum_redeem_points >= 0 AND (expiration_days IS NULL OR expiration_days > 0)", name="ck_loyalty_program_limits"),
        sa.CheckConstraint("max_discount_percent >= 0 AND max_discount_percent <= 100", name="ck_loyalty_discount_percent"),
    )
    op.create_index("ix_loyalty_program_organization_id", "loyalty_program", ["organization_id"])
    op.create_table(
        "loyalty_tier",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizacion.id_organizacion", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(40), nullable=False), sa.Column("name", sa.String(80), nullable=False),
        sa.Column("minimum_points", sa.Integer(), nullable=False),
        sa.UniqueConstraint("organization_id", "code", name="uq_loyalty_tier_org_code"),
    )
    op.create_index("ix_loyalty_tier_organization_id", "loyalty_tier", ["organization_id"])
    op.create_table(
        "loyalty_account",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizacion.id_organizacion", ondelete="CASCADE"), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("cliente.id_cliente", ondelete="RESTRICT"), nullable=False),
        sa.Column("balance", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("earned_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("redeemed_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expired_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "customer_id", name="uq_loyalty_account_org_customer"),
        sa.CheckConstraint("balance >= 0", name="ck_loyalty_balance_nonnegative"),
    )
    op.create_index("ix_loyalty_account_organization_id", "loyalty_account", ["organization_id"])
    op.create_index("ix_loyalty_account_customer_id", "loyalty_account", ["customer_id"])
    op.create_table(
        "loyalty_ledger",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizacion.id_organizacion", ondelete="CASCADE"), nullable=False),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("loyalty_account.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("pedido.id_pedido", ondelete="SET NULL"), nullable=True),
        sa.Column("event_key", sa.String(180), nullable=False), sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False), sa.Column("amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "event_key", name="uq_loyalty_ledger_org_event"),
        sa.CheckConstraint("points <> 0 OR kind IN ('EXPIRACION', 'REVERSO')", name="ck_loyalty_ledger_nonzero"),
    )
    op.create_index("ix_loyalty_ledger_organization_id", "loyalty_ledger", ["organization_id"])
    op.create_index("ix_loyalty_ledger_account_id", "loyalty_ledger", ["account_id"])
    op.create_index("ix_loyalty_ledger_order_id", "loyalty_ledger", ["order_id"])
    # Expose the assignable feature to platform plan management without enabling it for any current tenant.
    op.execute(sa.text("""INSERT INTO plan_caracteristica (plan_id, codigo, nombre, descripcion, habilitada)
        SELECT p.id_plan, 'fidelizacion_clientes', 'Fidelización de clientes',
               'CU12: programa de puntos y recompensas por organización', FALSE
        FROM plan p WHERE NOT EXISTS (
          SELECT 1 FROM plan_caracteristica pc WHERE pc.plan_id = p.id_plan AND pc.codigo = 'fidelizacion_clientes'
        )"""))


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM plan_caracteristica WHERE codigo = 'fidelizacion_clientes' AND descripcion = 'CU12: programa de puntos y recompensas por organización'"))
    op.drop_index("ix_loyalty_ledger_order_id", table_name="loyalty_ledger")
    op.drop_index("ix_loyalty_ledger_account_id", table_name="loyalty_ledger")
    op.drop_index("ix_loyalty_ledger_organization_id", table_name="loyalty_ledger")
    op.drop_table("loyalty_ledger")
    op.drop_index("ix_loyalty_account_customer_id", table_name="loyalty_account")
    op.drop_index("ix_loyalty_account_organization_id", table_name="loyalty_account")
    op.drop_table("loyalty_account")
    op.drop_index("ix_loyalty_tier_organization_id", table_name="loyalty_tier")
    op.drop_table("loyalty_tier")
    op.drop_index("ix_loyalty_program_organization_id", table_name="loyalty_program")
    op.drop_table("loyalty_program")
