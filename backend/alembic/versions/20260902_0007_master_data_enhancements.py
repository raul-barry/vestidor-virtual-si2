"""Add estado to categoria, talla, color and ciudad to sucursal.

Revision ID: 20260902_0007
Revises: 20260902_0006
Create Date: 2026-09-02 00:00:07.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260902_0007"
down_revision: Union[str, Sequence[str], None] = "20260902_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "categoria",
        sa.Column("estado", sa.String(length=30), nullable=False, server_default="ACTIVO"),
    )
    op.add_column(
        "talla",
        sa.Column("estado", sa.String(length=30), nullable=False, server_default="ACTIVO"),
    )
    op.add_column(
        "color",
        sa.Column("estado", sa.String(length=30), nullable=False, server_default="ACTIVO"),
    )
    op.add_column(
        "sucursal",
        sa.Column("ciudad", sa.String(length=100), nullable=False, server_default="Santa Cruz"),
    )


def downgrade() -> None:
    op.drop_column("sucursal", "ciudad")
    op.drop_column("color", "estado")
    op.drop_column("talla", "estado")
    op.drop_column("categoria", "estado")
