"""Proveedores, colecciones, promociones y devoluciones."""
from alembic import op
import sqlalchemy as sa

revision = "20260913_0009"
down_revision = "20260913_0008"
branch_labels = None
depends_on = None


def upgrade():
    for table, extra in [("proveedor", "contacto"), ("coleccion", "descripcion")]:
        op.create_table(table,
            sa.Column(f"id_{table}", sa.Integer(), primary_key=True),
            sa.Column("nombre", sa.String(150), nullable=False, unique=True),
            sa.Column(extra, sa.String(255), nullable=False),
            sa.Column("estado", sa.String(30), nullable=False))
    with op.batch_alter_table("producto") as batch:
        for name in ("proveedor", "coleccion"):
            batch.add_column(sa.Column(f"id_{name}", sa.Integer(), nullable=True))
            batch.create_foreign_key(f"fk_producto_{name}", name, [f"id_{name}"], [f"id_{name}"])
    op.create_table("promocion",
        sa.Column("id_promocion", sa.Integer(), primary_key=True),
        sa.Column("id_producto", sa.Integer(), sa.ForeignKey("producto.id_producto"), nullable=False),
        sa.Column("nombre", sa.String(150), nullable=False),
        sa.Column("descuento", sa.Numeric(5, 2), nullable=False),
        sa.Column("inicio", sa.Date(), nullable=False),
        sa.Column("fin", sa.Date(), nullable=False),
        sa.Column("estado", sa.String(30), nullable=False),
        sa.CheckConstraint("descuento > 0 AND descuento <= 100", name="ck_promocion_descuento"))
    op.create_index("ix_promocion_id_producto", "promocion", ["id_producto"])
    op.create_table("devolucion",
        sa.Column("id_devolucion", sa.Integer(), primary_key=True),
        sa.Column("id_detalle", sa.Integer(), sa.ForeignKey("pedido_detalle.id_detalle"), nullable=False),
        sa.Column("id_inventario", sa.Integer(), sa.ForeignKey("inventario.id_inventario"), nullable=False),
        sa.Column("id_usuario", sa.Integer(), sa.ForeignKey("usuario.id_usuario"), nullable=False),
        sa.Column("cantidad", sa.Integer(), nullable=False),
        sa.Column("motivo", sa.String(255), nullable=False),
        sa.Column("fecha", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("cantidad > 0", name="ck_devolucion_cantidad"))
    op.create_index("ix_devolucion_id_detalle", "devolucion", ["id_detalle"])


def downgrade():
    op.drop_table("devolucion")
    op.drop_table("promocion")
    with op.batch_alter_table("producto") as batch:
        for name in ("coleccion", "proveedor"):
            batch.drop_constraint(f"fk_producto_{name}", type_="foreignkey")
            batch.drop_column(f"id_{name}")
    op.drop_table("coleccion")
    op.drop_table("proveedor")
