"""Completa datos administrativos de proveedores y colecciones."""

from alembic import op
import sqlalchemy as sa

revision = "20260919_0016"
down_revision = "20260919_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("proveedor", sa.Column("descripcion", sa.String(500), nullable=False, server_default=""))
    op.add_column("proveedor", sa.Column("persona_contacto", sa.String(150), nullable=False, server_default=""))
    op.add_column("proveedor", sa.Column("telefono", sa.String(30), nullable=False, server_default=""))
    op.add_column("proveedor", sa.Column("correo", sa.String(255), nullable=False, server_default=""))
    op.add_column("proveedor", sa.Column("direccion", sa.String(255), nullable=False, server_default=""))
    op.execute("UPDATE proveedor SET persona_contacto = contacto WHERE contacto IS NOT NULL AND contacto <> ''")

    op.add_column("coleccion", sa.Column("temporada", sa.String(80), nullable=False, server_default=""))
    op.add_column("coleccion", sa.Column("anio", sa.Integer(), nullable=True))
    op.add_column("coleccion", sa.Column("fecha_inicio", sa.Date(), nullable=True))
    op.add_column("coleccion", sa.Column("fecha_fin", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("coleccion", "fecha_fin")
    op.drop_column("coleccion", "fecha_inicio")
    op.drop_column("coleccion", "anio")
    op.drop_column("coleccion", "temporada")
    op.drop_column("proveedor", "direccion")
    op.drop_column("proveedor", "correo")
    op.drop_column("proveedor", "telefono")
    op.drop_column("proveedor", "persona_contacto")
    op.drop_column("proveedor", "descripcion")
