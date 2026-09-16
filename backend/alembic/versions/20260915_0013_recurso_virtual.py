"""Product visual assets, with a reserved type for future 3D viewers."""
from alembic import op
import sqlalchemy as sa

revision = "20260915_0013"
down_revision = "20260915_0012"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "recurso_virtual",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("id_producto", sa.Integer(), sa.ForeignKey("producto.id_producto"), nullable=False),
        sa.Column("tipo_recurso", sa.String(30), nullable=False, server_default="imagen"),
        sa.Column("url_archivo", sa.String(500), nullable=False),
        sa.Column("estado", sa.String(30), nullable=False, server_default="ACTIVO"),
        sa.UniqueConstraint("id_producto", "url_archivo"),
        sa.CheckConstraint("tipo_recurso IN ('imagen', 'modelo_3d')"),
        sa.CheckConstraint("estado IN ('ACTIVO', 'INACTIVO')"),
    )
    op.create_index("ix_recurso_virtual_id_producto", "recurso_virtual", ["id_producto"])


def downgrade():
    op.drop_table("recurso_virtual")
