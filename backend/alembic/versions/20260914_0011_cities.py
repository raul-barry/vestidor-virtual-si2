"""Directorio de ciudades a partir de las sucursales existentes."""
from alembic import op
import sqlalchemy as sa
revision = "20260914_0011"
down_revision = "20260914_0010"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("ciudad",
        sa.Column("id_ciudad", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(100), nullable=False, unique=True),
        sa.Column("descripcion", sa.String(255), nullable=False),
        sa.Column("estado", sa.String(30), nullable=False))
    op.execute("INSERT INTO ciudad (nombre, descripcion, estado) SELECT DISTINCT ciudad, '', 'ACTIVO' FROM sucursal")


def downgrade():
    op.drop_table("ciudad")
