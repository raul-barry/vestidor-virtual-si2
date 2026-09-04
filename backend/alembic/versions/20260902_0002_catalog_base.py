"""Create catalog base tables.

Revision ID: 20260902_0002
Revises: 20260902_0001
Create Date: 2026-09-02 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260902_0002"
down_revision: Union[str, Sequence[str], None] = "20260902_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "categoria",
        sa.Column("id_categoria", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column("descripcion", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id_categoria"),
        sa.UniqueConstraint("nombre"),
    )
    op.create_table(
        "talla",
        sa.Column("id_talla", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=20), nullable=False),
        sa.PrimaryKeyConstraint("id_talla"),
        sa.UniqueConstraint("nombre"),
    )
    op.create_table(
        "color",
        sa.Column("id_color", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint("id_color"),
        sa.UniqueConstraint("nombre"),
    )
    op.create_table(
        "sucursal",
        sa.Column("id_sucursal", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=150), nullable=False),
        sa.Column("direccion", sa.String(length=255), nullable=False),
        sa.Column("estado", sa.String(length=30), nullable=False),
        sa.PrimaryKeyConstraint("id_sucursal"),
        sa.UniqueConstraint("nombre"),
    )
    op.create_table(
        "producto",
        sa.Column("id_producto", sa.Integer(), nullable=False),
        sa.Column("id_categoria", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=150), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("precio_base", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("estado", sa.String(length=30), nullable=False),
        sa.Column("fecha_creacion", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["id_categoria"], ["categoria.id_categoria"]),
        sa.PrimaryKeyConstraint("id_producto"),
    )
    op.create_index("ix_producto_id_categoria", "producto", ["id_categoria"], unique=False)
    op.create_table(
        "producto_variante",
        sa.Column("id_variante", sa.Integer(), nullable=False),
        sa.Column("id_producto", sa.Integer(), nullable=False),
        sa.Column("id_talla", sa.Integer(), nullable=False),
        sa.Column("id_color", sa.Integer(), nullable=False),
        sa.Column("sku", sa.String(length=100), nullable=False),
        sa.Column("estado", sa.String(length=30), nullable=False),
        sa.ForeignKeyConstraint(["id_color"], ["color.id_color"]),
        sa.ForeignKeyConstraint(["id_producto"], ["producto.id_producto"]),
        sa.ForeignKeyConstraint(["id_talla"], ["talla.id_talla"]),
        sa.PrimaryKeyConstraint("id_variante"),
        sa.UniqueConstraint("sku"),
        sa.UniqueConstraint("id_producto", "id_talla", "id_color"),
    )
    op.create_index("ix_producto_variante_id_producto", "producto_variante", ["id_producto"], unique=False)
    op.create_index("ix_producto_variante_id_talla", "producto_variante", ["id_talla"], unique=False)
    op.create_index("ix_producto_variante_id_color", "producto_variante", ["id_color"], unique=False)
    op.create_table(
        "inventario",
        sa.Column("id_inventario", sa.Integer(), nullable=False),
        sa.Column("id_sucursal", sa.Integer(), nullable=False),
        sa.Column("id_variante", sa.Integer(), nullable=False),
        sa.Column("stock_disponible", sa.Integer(), nullable=False),
        sa.Column("stock_reservado", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["id_sucursal"], ["sucursal.id_sucursal"]),
        sa.ForeignKeyConstraint(["id_variante"], ["producto_variante.id_variante"]),
        sa.PrimaryKeyConstraint("id_inventario"),
        sa.UniqueConstraint("id_sucursal", "id_variante"),
    )
    op.create_index("ix_inventario_id_sucursal", "inventario", ["id_sucursal"], unique=False)
    op.create_index("ix_inventario_id_variante", "inventario", ["id_variante"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_inventario_id_variante", table_name="inventario")
    op.drop_index("ix_inventario_id_sucursal", table_name="inventario")
    op.drop_table("inventario")
    op.drop_index("ix_producto_variante_id_color", table_name="producto_variante")
    op.drop_index("ix_producto_variante_id_talla", table_name="producto_variante")
    op.drop_index("ix_producto_variante_id_producto", table_name="producto_variante")
    op.drop_table("producto_variante")
    op.drop_index("ix_producto_id_categoria", table_name="producto")
    op.drop_table("producto")
    op.drop_table("sucursal")
    op.drop_table("color")
    op.drop_table("talla")
    op.drop_table("categoria")
