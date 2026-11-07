"""Create immutable tenant activity log."""
from alembic import op
import sqlalchemy as sa

revision = "20261103_0030"
down_revision = "20261103_0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organizacion_id", sa.Integer(), sa.ForeignKey("organizacion.id_organizacion", ondelete="RESTRICT"), nullable=False),
        sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("usuario.id_usuario", ondelete="SET NULL"), nullable=True),
        sa.Column("rol", sa.String(40), nullable=False),
        sa.Column("accion", sa.String(80), nullable=False),
        sa.Column("entidad", sa.String(80), nullable=False),
        sa.Column("entidad_id", sa.String(80)),
        sa.Column("fecha_hora", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("resultado", sa.String(30), server_default="EXITOSO", nullable=False),
        sa.Column("detalles", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
    )
    op.create_index("ix_audit_log_org_fecha", "audit_log", ["organizacion_id", "fecha_hora"])
    op.create_index("ix_audit_log_org_accion", "audit_log", ["organizacion_id", "accion"])
    op.create_index("ix_audit_log_org_usuario", "audit_log", ["organizacion_id", "usuario_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_log_org_usuario", table_name="audit_log")
    op.drop_index("ix_audit_log_org_accion", table_name="audit_log")
    op.drop_index("ix_audit_log_org_fecha", table_name="audit_log")
    op.drop_table("audit_log")
