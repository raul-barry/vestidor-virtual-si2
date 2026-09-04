"""Create inventory movement history table.

Revision ID: 20260902_0006
Revises: 20260902_0005
Create Date: 2026-09-02 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260902_0006"
down_revision: Union[str, Sequence[str], None] = "20260902_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "movimiento_inventario",
        sa.Column("id_movimiento", sa.Integer(), nullable=False),
        sa.Column("id_inventario", sa.Integer(), nullable=False),
        sa.Column("tipo_movimiento", sa.String(length=20), nullable=False),
        sa.Column("cantidad", sa.Integer(), nullable=False),
        sa.Column("stock_anterior", sa.Integer(), nullable=False),
        sa.Column("stock_nuevo", sa.Integer(), nullable=False),
        sa.Column("motivo", sa.String(length=255), nullable=False),
        sa.Column("fecha_movimiento", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id_usuario", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["id_inventario"], ["inventario.id_inventario"]),
        sa.ForeignKeyConstraint(["id_usuario"], ["usuario.id_usuario"]),
        sa.PrimaryKeyConstraint("id_movimiento"),
    )
    op.create_index("ix_movimiento_inventario_id_inventario", "movimiento_inventario", ["id_inventario"], unique=False)
    op.create_index("ix_movimiento_inventario_id_usuario", "movimiento_inventario", ["id_usuario"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_movimiento_inventario_id_usuario", table_name="movimiento_inventario")
    op.drop_index("ix_movimiento_inventario_id_inventario", table_name="movimiento_inventario")
    op.drop_table("movimiento_inventario")
