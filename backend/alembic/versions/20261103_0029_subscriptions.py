"""Add organization SaaS subscriptions."""

from alembic import op
import sqlalchemy as sa


revision = "20261103_0029"
down_revision = "20261103_0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "suscripcion",
        sa.Column("id_suscripcion", sa.Integer(), primary_key=True),
        sa.Column(
            "organizacion_id",
            sa.Integer(),
            sa.ForeignKey("organizacion.id_organizacion", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "plan_id",
            sa.Integer(),
            sa.ForeignKey("plan.id_plan", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("estado", sa.String(length=20), server_default="ACTIVA", nullable=False),
        sa.Column("fecha_inicio", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_fin", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "fecha_creacion", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.Column(
            "fecha_actualizacion", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.Column(
            "creado_por_id",
            sa.Integer(),
            sa.ForeignKey("usuario.id_usuario", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.CheckConstraint(
            "estado IN ('ACTIVA', 'VENCIDA', 'CANCELADA', 'FINALIZADA')",
            name="ck_suscripcion_estado",
        ),
        sa.CheckConstraint(
            "fecha_fin IS NULL OR fecha_fin > fecha_inicio",
            name="ck_suscripcion_fecha_fin_posterior_inicio",
        ),
    )
    op.create_index("ix_suscripcion_organizacion_id", "suscripcion", ["organizacion_id"])
    op.create_index("ix_suscripcion_plan_id", "suscripcion", ["plan_id"])
    op.create_index("ix_suscripcion_creado_por_id", "suscripcion", ["creado_por_id"])
    op.create_index(
        "uq_suscripcion_organizacion_activa",
        "suscripcion",
        ["organizacion_id"],
        unique=True,
        postgresql_where=sa.text("estado = 'ACTIVA'"),
        sqlite_where=sa.text("estado = 'ACTIVA'"),
    )


def downgrade() -> None:
    op.drop_index("uq_suscripcion_organizacion_activa", table_name="suscripcion")
    op.drop_index("ix_suscripcion_creado_por_id", table_name="suscripcion")
    op.drop_index("ix_suscripcion_plan_id", table_name="suscripcion")
    op.drop_index("ix_suscripcion_organizacion_id", table_name="suscripcion")
    op.drop_table("suscripcion")
