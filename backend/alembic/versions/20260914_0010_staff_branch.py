"""Asignación de empleados a sucursales."""
from alembic import op
import sqlalchemy as sa
revision = "20260914_0010"
down_revision = "20260913_0009"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("usuario") as batch:
        batch.add_column(sa.Column("id_sucursal", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_usuario_sucursal", "sucursal", ["id_sucursal"], ["id_sucursal"])


def downgrade():
    with op.batch_alter_table("usuario") as batch:
        batch.drop_constraint("fk_usuario_sucursal", type_="foreignkey")
        batch.drop_column("id_sucursal")
