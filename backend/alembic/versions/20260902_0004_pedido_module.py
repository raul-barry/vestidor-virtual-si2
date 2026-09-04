"""Create order module tables.

Revision ID: 20260902_0004
Revises: 20260902_0003
Create Date: 2026-09-02 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260902_0004"
down_revision: Union[str, Sequence[str], None] = "20260902_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pedido",
        sa.Column("id_pedido", sa.Integer(), nullable=False),
        sa.Column("id_cliente", sa.Integer(), nullable=False),
        sa.Column("fecha_pedido", sa.DateTime(timezone=True), nullable=False),
        sa.Column("estado", sa.String(length=30), nullable=False),
        sa.Column("total", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.ForeignKeyConstraint(["id_cliente"], ["cliente.id_cliente"]),
        sa.PrimaryKeyConstraint("id_pedido"),
    )
    op.create_index("ix_pedido_id_cliente", "pedido", ["id_cliente"], unique=False)
    op.create_table(
        "pedido_detalle",
        sa.Column("id_detalle", sa.Integer(), nullable=False),
        sa.Column("id_pedido", sa.Integer(), nullable=False),
        sa.Column("id_variante", sa.Integer(), nullable=False),
        sa.Column("cantidad", sa.Integer(), nullable=False),
        sa.Column("precio_unitario", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.ForeignKeyConstraint(["id_pedido"], ["pedido.id_pedido"]),
        sa.ForeignKeyConstraint(["id_variante"], ["producto_variante.id_variante"]),
        sa.PrimaryKeyConstraint("id_detalle"),
    )
    op.create_index("ix_pedido_detalle_id_pedido", "pedido_detalle", ["id_pedido"], unique=False)
    op.create_index("ix_pedido_detalle_id_variante", "pedido_detalle", ["id_variante"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_pedido_detalle_id_variante", table_name="pedido_detalle")
    op.drop_index("ix_pedido_detalle_id_pedido", table_name="pedido_detalle")
    op.drop_table("pedido_detalle")
    op.drop_index("ix_pedido_id_cliente", table_name="pedido")
    op.drop_table("pedido")
