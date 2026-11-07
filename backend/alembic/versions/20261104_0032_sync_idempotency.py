"""Add tenant-scoped offline sync idempotency records."""
from alembic import op
import sqlalchemy as sa


revision = "20261104_0032"
down_revision = "20261103_0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sync_idempotency",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organizacion_id", sa.Integer(), sa.ForeignKey("organizacion.id_organizacion", ondelete="RESTRICT"), nullable=False),
        sa.Column("operation_uuid", sa.String(36), nullable=False),
        sa.Column("operation_type", sa.String(80), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("client_id", sa.String(100), nullable=False),
        sa.Column("tenant_scope", sa.String(180), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("operation_created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=False),
        sa.Column("error_code", sa.String(60)),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organizacion_id", "operation_uuid", name="uq_sync_org_operation_uuid"),
    )
    op.create_index("ix_sync_org_status", "sync_idempotency", ["organizacion_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_sync_org_status", table_name="sync_idempotency")
    op.drop_table("sync_idempotency")
