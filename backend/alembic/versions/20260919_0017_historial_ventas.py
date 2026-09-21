"""Registra el vendedor de ventas presenciales para el historial comercial."""
from alembic import op
import sqlalchemy as sa

revision = "20260919_0017"
down_revision = "20260919_0016"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("pedido", sa.Column("id_vendedor", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_pedido_vendedor_usuario", "pedido", "usuario", ["id_vendedor"], ["id_usuario"])
    op.create_index("ix_pedido_id_vendedor", "pedido", ["id_vendedor"])

def downgrade() -> None:
    op.drop_index("ix_pedido_id_vendedor", table_name="pedido")
    op.drop_constraint("fk_pedido_vendedor_usuario", "pedido", type_="foreignkey")
    op.drop_column("pedido", "id_vendedor")
