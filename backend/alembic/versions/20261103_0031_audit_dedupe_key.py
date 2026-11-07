"""Add idempotency key for lifecycle audit events."""
from alembic import op
import sqlalchemy as sa

revision = "20261103_0031"
down_revision = "20261103_0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("audit_log", sa.Column("dedupe_key", sa.String(length=160), nullable=True))
    op.create_index("uq_audit_log_dedupe_key", "audit_log", ["dedupe_key"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_audit_log_dedupe_key", table_name="audit_log")
    op.drop_column("audit_log", "dedupe_key")
