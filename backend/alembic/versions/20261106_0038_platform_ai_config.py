"""Add encrypted platform-wide AI provider configuration."""
from alembic import op
import sqlalchemy as sa


revision = "20261106_0038"
down_revision = "20261106_0037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "platform_ai_config",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("encrypted_api_key", sa.Text(), nullable=True),
        sa.Column("models", sa.JSON(), nullable=False),
        sa.Column("last_test_status", sa.String(24), nullable=True),
        sa.Column("last_test_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_platform_ai_config_singleton"),
    )
    op.create_table(
        "platform_ai_config_audit",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("usuario.id_usuario", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("result", sa.String(24), nullable=False),
        sa.Column("model_ids", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_platform_ai_config_audit_actor_id", "platform_ai_config_audit", ["actor_id"])


def downgrade() -> None:
    op.drop_index("ix_platform_ai_config_audit_actor_id", table_name="platform_ai_config_audit")
    op.drop_table("platform_ai_config_audit")
    op.drop_table("platform_ai_config")
