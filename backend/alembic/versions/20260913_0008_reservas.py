"""Reservas de prendas."""
from alembic import op
import sqlalchemy as sa

revision = "20260913_0008"
down_revision = "20260902_0007"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("reserva",
        sa.Column("id_reserva", sa.Integer(), primary_key=True),
        sa.Column("id_usuario", sa.Integer(), sa.ForeignKey("usuario.id_usuario"), nullable=False),
        sa.Column("id_inventario", sa.Integer(), sa.ForeignKey("inventario.id_inventario"), nullable=False),
        sa.Column("cantidad", sa.Integer(), nullable=False),
        sa.Column("estado", sa.String(30), nullable=False),
        sa.Column("fecha", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("cantidad > 0", name="ck_reserva_cantidad"))
    op.create_index("ix_reserva_id_usuario", "reserva", ["id_usuario"])
    op.create_index("ix_reserva_id_inventario", "reserva", ["id_inventario"])


def downgrade():
    op.drop_table("reserva")
