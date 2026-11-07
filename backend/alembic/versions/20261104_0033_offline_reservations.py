"""Persist reservation expiry and limited device sync credentials."""
from alembic import op
import sqlalchemy as sa


revision = "20261104_0033"
down_revision = "20261104_0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("reserva", sa.Column("fecha_expiracion", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "device_sync_credential",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organizacion_id", sa.Integer(), sa.ForeignKey("organizacion.id_organizacion", ondelete="CASCADE"), nullable=False),
        sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("usuario.id_usuario", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", sa.String(100), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("token_hash", name="uq_device_sync_credential_token_hash"),
    )
    op.create_index("ix_device_sync_credential_org_user", "device_sync_credential", ["organizacion_id", "usuario_id"])


def downgrade() -> None:
    op.drop_index("ix_device_sync_credential_org_user", table_name="device_sync_credential")
    op.drop_table("device_sync_credential")
    op.drop_column("reserva", "fecha_expiracion")
