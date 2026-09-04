"""Create payment module table.

Revision ID: 20260902_0005
Revises: 20260902_0004
Create Date: 2026-09-02 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260902_0005"
down_revision: Union[str, Sequence[str], None] = "20260902_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pago",
        sa.Column("id_pago", sa.Integer(), nullable=False),
        sa.Column("id_pedido", sa.Integer(), nullable=False),
        sa.Column("metodo_pago", sa.String(length=30), nullable=False),
        sa.Column("monto", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("fecha_pago", sa.DateTime(timezone=True), nullable=False),
        sa.Column("estado", sa.String(length=30), nullable=False),
        sa.ForeignKeyConstraint(["id_pedido"], ["pedido.id_pedido"]),
        sa.PrimaryKeyConstraint("id_pago"),
        sa.UniqueConstraint("id_pedido"),
    )
    op.create_index("ix_pago_id_pedido", "pago", ["id_pedido"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_pago_id_pedido", table_name="pago")
    op.drop_table("pago")
