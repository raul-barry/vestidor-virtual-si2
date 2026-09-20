"""Roles dinámicos y permisos administrativos."""
from alembic import op
import sqlalchemy as sa

revision = "20260919_0015"
down_revision = "20260919_0014"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("rol", sa.Column("estado", sa.String(30), nullable=False, server_default="ACTIVO"))
    op.create_table("permiso", sa.Column("id_permiso", sa.Integer(), primary_key=True), sa.Column("codigo", sa.String(100), nullable=False, unique=True), sa.Column("descripcion", sa.String(255)))
    op.create_table("rol_permiso", sa.Column("id_rol", sa.Integer(), sa.ForeignKey("rol.id_rol", ondelete="CASCADE"), primary_key=True), sa.Column("id_permiso", sa.Integer(), sa.ForeignKey("permiso.id_permiso", ondelete="CASCADE"), primary_key=True))
    permisos = sa.table("permiso", sa.column("codigo", sa.String), sa.column("descripcion", sa.String))
    op.bulk_insert(permisos, [
        {"codigo":"USUARIOS_GESTIONAR","descripcion":"Administrar usuarios"},
        {"codigo":"CATALOGO_GESTIONAR","descripcion":"Administrar catálogo"},
        {"codigo":"INVENTARIO_GESTIONAR","descripcion":"Administrar inventario"},
        {"codigo":"VENTAS_REGISTRAR","descripcion":"Registrar ventas"},
        {"codigo":"REPORTES_CONSULTAR","descripcion":"Consultar reportes"},
    ])

def downgrade():
    op.drop_table("rol_permiso")
    op.drop_table("permiso")
    op.drop_column("rol", "estado")
