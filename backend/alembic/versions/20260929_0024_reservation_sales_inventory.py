"""Track sold inventory and preserve reservation-to-order checkout links."""
from alembic import op
import sqlalchemy as sa

revision = "20260929_0024"
down_revision = "20260920_0023"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("inventario", sa.Column("stock_vendido", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("reserva", sa.Column("id_pedido", sa.Integer(), nullable=True))
    op.create_index("ix_reserva_id_pedido", "reserva", ["id_pedido"])
    op.create_foreign_key("fk_reserva_id_pedido", "reserva", "pedido", ["id_pedido"], ["id_pedido"])
    op.add_column("carrito_detalle", sa.Column("id_reserva", sa.Integer(), nullable=True))
    op.create_index("ix_carrito_detalle_id_reserva", "carrito_detalle", ["id_reserva"])
    op.create_foreign_key("fk_carrito_detalle_id_reserva", "carrito_detalle", "reserva", ["id_reserva"], ["id_reserva"])
    op.add_column("pedido_detalle", sa.Column("id_reserva", sa.Integer(), nullable=True))
    op.create_index("ix_pedido_detalle_id_reserva", "pedido_detalle", ["id_reserva"])
    op.create_foreign_key("fk_pedido_detalle_id_reserva", "pedido_detalle", "reserva", ["id_reserva"], ["id_reserva"])


def downgrade():
    op.drop_constraint("fk_pedido_detalle_id_reserva", "pedido_detalle", type_="foreignkey")
    op.drop_index("ix_pedido_detalle_id_reserva", table_name="pedido_detalle")
    op.drop_column("pedido_detalle", "id_reserva")
    op.drop_constraint("fk_carrito_detalle_id_reserva", "carrito_detalle", type_="foreignkey")
    op.drop_index("ix_carrito_detalle_id_reserva", table_name="carrito_detalle")
    op.drop_column("carrito_detalle", "id_reserva")
    op.drop_constraint("fk_reserva_id_pedido", "reserva", type_="foreignkey")
    op.drop_index("ix_reserva_id_pedido", table_name="reserva")
    op.drop_column("reserva", "id_pedido")
    op.drop_column("inventario", "stock_vendido")
