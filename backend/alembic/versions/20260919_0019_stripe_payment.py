"""Stripe payment provider metadata."""
from alembic import op
import sqlalchemy as sa

revision = "20260919_0019"
down_revision = "20260919_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pago", sa.Column("proveedor", sa.String(length=30), nullable=True))
    op.add_column("pago", sa.Column("referencia_externa", sa.String(length=255), nullable=True))
    op.add_column("pago", sa.Column("evento_externo", sa.String(length=255), nullable=True))
    op.create_index("ix_pago_referencia_externa", "pago", ["referencia_externa"], unique=True)
    op.create_index("ix_pago_evento_externo", "pago", ["evento_externo"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_pago_evento_externo", table_name="pago")
    op.drop_index("ix_pago_referencia_externa", table_name="pago")
    op.drop_column("pago", "evento_externo")
    op.drop_column("pago", "referencia_externa")
    op.drop_column("pago", "proveedor")
