"""Campos comerciales de pedido: consumidor final, factura y entrega.

Equivalente Alembic de database/scripts/0001_pedido_comercial.sql.
"""
from alembic import op
import sqlalchemy as sa

revision = "20260919_0014"
down_revision = "20260915_0013"
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table("pedido") as batch:
        batch.alter_column("id_cliente", existing_type=sa.Integer(), nullable=True)
        batch.add_column(sa.Column("tipo_cliente", sa.String(30), nullable=False, server_default="CLIENTE_REGISTRADO"))
        batch.add_column(sa.Column("tipo_venta", sa.String(30), nullable=False, server_default="ONLINE"))
        batch.add_column(sa.Column("nit_ci", sa.String(30)))
        batch.add_column(sa.Column("razon_social", sa.String(150)))
        batch.add_column(sa.Column("tipo_entrega", sa.String(30)))
        batch.add_column(sa.Column("id_sucursal_entrega", sa.Integer()))
        batch.create_foreign_key(
            "fk_pedido_sucursal_entrega",
            "sucursal",
            ["id_sucursal_entrega"],
            ["id_sucursal"],
        )
        batch.add_column(sa.Column("direccion_entrega", sa.String(255)))
        batch.add_column(sa.Column("referencia_entrega", sa.String(255)))
        batch.add_column(sa.Column("telefono_entrega", sa.String(30)))

def downgrade():
    with op.batch_alter_table("pedido") as batch:
        batch.drop_constraint("fk_pedido_sucursal_entrega", type_="foreignkey")
        for column in ("telefono_entrega", "referencia_entrega", "direccion_entrega", "id_sucursal_entrega", "tipo_entrega", "razon_social", "nit_ci", "tipo_venta", "tipo_cliente"):
            batch.drop_column(column)
        batch.alter_column("id_cliente", existing_type=sa.Integer(), nullable=False)
