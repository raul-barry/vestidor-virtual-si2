"""Create initial user and security tables.

Revision ID: 20260902_0001
Revises:
Create Date: 2026-09-02 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260902_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rol",
        sa.Column("id_rol", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column("descripcion", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id_rol"),
        sa.UniqueConstraint("nombre"),
    )
    op.create_table(
        "usuario",
        sa.Column("id_usuario", sa.Integer(), nullable=False),
        sa.Column("id_rol", sa.Integer(), nullable=False),
        sa.Column("nombres", sa.String(length=100), nullable=False),
        sa.Column("apellidos", sa.String(length=100), nullable=False),
        sa.Column("correo", sa.String(length=255), nullable=False),
        sa.Column("telefono", sa.String(length=30), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("estado", sa.String(length=30), nullable=False),
        sa.Column("fecha_registro", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["id_rol"], ["rol.id_rol"]),
        sa.PrimaryKeyConstraint("id_usuario"),
        sa.UniqueConstraint("correo"),
    )
    op.create_index("ix_usuario_id_rol", "usuario", ["id_rol"], unique=False)
    op.create_table(
        "cliente",
        sa.Column("id_cliente", sa.Integer(), nullable=False),
        sa.Column("id_usuario", sa.Integer(), nullable=False),
        sa.Column("fecha_registro", sa.DateTime(timezone=True), nullable=False),
        sa.Column("estado", sa.String(length=30), nullable=False),
        sa.ForeignKeyConstraint(["id_usuario"], ["usuario.id_usuario"]),
        sa.PrimaryKeyConstraint("id_cliente"),
        sa.UniqueConstraint("id_usuario"),
    )
    op.create_table(
        "sesion",
        sa.Column("id_sesion", sa.Integer(), nullable=False),
        sa.Column("id_usuario", sa.Integer(), nullable=False),
        sa.Column("token_jwt", sa.String(length=2048), nullable=False),
        sa.Column("fecha_inicio", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_expiracion", sa.DateTime(timezone=True), nullable=False),
        sa.Column("estado", sa.String(length=30), nullable=False),
        sa.ForeignKeyConstraint(["id_usuario"], ["usuario.id_usuario"]),
        sa.PrimaryKeyConstraint("id_sesion"),
    )
    op.create_index("ix_sesion_id_usuario", "sesion", ["id_usuario"], unique=False)
    op.create_table(
        "token_recuperacion",
        sa.Column("id_token", sa.Integer(), nullable=False),
        sa.Column("id_usuario", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(length=255), nullable=False),
        sa.Column("fecha_expiracion", sa.DateTime(timezone=True), nullable=False),
        sa.Column("usado", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["id_usuario"], ["usuario.id_usuario"]),
        sa.PrimaryKeyConstraint("id_token"),
        sa.UniqueConstraint("token"),
    )
    op.create_index("ix_token_recuperacion_id_usuario", "token_recuperacion", ["id_usuario"], unique=False)
    op.create_table(
        "bitacora",
        sa.Column("nro_bitacora", sa.Integer(), nullable=False),
        sa.Column("id_usuario", sa.Integer(), nullable=False),
        sa.Column("accion", sa.String(length=255), nullable=False),
        sa.Column("fecha_hora", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["id_usuario"], ["usuario.id_usuario"]),
        sa.PrimaryKeyConstraint("nro_bitacora"),
    )
    op.create_index("ix_bitacora_id_usuario", "bitacora", ["id_usuario"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_bitacora_id_usuario", table_name="bitacora")
    op.drop_table("bitacora")
    op.drop_index("ix_token_recuperacion_id_usuario", table_name="token_recuperacion")
    op.drop_table("token_recuperacion")
    op.drop_index("ix_sesion_id_usuario", table_name="sesion")
    op.drop_table("sesion")
    op.drop_table("cliente")
    op.drop_index("ix_usuario_id_rol", table_name="usuario")
    op.drop_table("usuario")
    op.drop_table("rol")
