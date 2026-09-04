"""Create cart module tables.

Revision ID: 20260902_0003
Revises: 20260902_0002
Create Date: 2026-09-02 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260902_0003"
down_revision: Union[str, Sequence[str], None] = "20260902_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "carrito",
        sa.Column("id_carrito", sa.Integer(), nullable=False),
        sa.Column("id_cliente", sa.Integer(), nullable=False),
        sa.Column("estado", sa.String(length=30), nullable=False),
        sa.Column("fecha_creacion", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_actualizacion", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["id_cliente"], ["cliente.id_cliente"]),
        sa.PrimaryKeyConstraint("id_carrito"),
        sa.UniqueConstraint("id_cliente"),
    )
    op.create_index("ix_carrito_id_cliente", "carrito", ["id_cliente"], unique=False)
    op.create_table(
        "carrito_detalle",
        sa.Column("id_detalle", sa.Integer(), nullable=False),
        sa.Column("id_carrito", sa.Integer(), nullable=False),
        sa.Column("id_variante", sa.Integer(), nullable=False),
        sa.Column("cantidad", sa.Integer(), nullable=False),
        sa.Column("precio_unitario", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.ForeignKeyConstraint(["id_carrito"], ["carrito.id_carrito"]),
        sa.ForeignKeyConstraint(["id_variante"], ["producto_variante.id_variante"]),
        sa.PrimaryKeyConstraint("id_detalle"),
        sa.UniqueConstraint("id_carrito", "id_variante"),
    )
    op.create_index("ix_carrito_detalle_id_carrito", "carrito_detalle", ["id_carrito"], unique=False)
    op.create_index("ix_carrito_detalle_id_variante", "carrito_detalle", ["id_variante"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_carrito_detalle_id_variante", table_name="carrito_detalle")
    op.drop_index("ix_carrito_detalle_id_carrito", table_name="carrito_detalle")
    op.drop_table("carrito_detalle")
    op.drop_index("ix_carrito_id_cliente", table_name="carrito")
    op.drop_table("carrito")
