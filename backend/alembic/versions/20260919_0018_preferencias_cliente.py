"""Preferencias persistentes del cliente."""
from alembic import op
import sqlalchemy as sa
revision = "20260919_0018"
down_revision = "20260919_0017"
branch_labels = None
depends_on = None
def upgrade() -> None:
    op.create_table("preferencia_cliente", sa.Column("id_preferencia",sa.Integer(),primary_key=True),sa.Column("id_cliente",sa.Integer(),sa.ForeignKey("cliente.id_cliente"),nullable=False,unique=True),sa.Column("talla_superior",sa.String(50)),sa.Column("talla_pantalon",sa.String(50)),sa.Column("talla_calzado",sa.String(50)),sa.Column("estilos",sa.String(500),nullable=False,server_default=""))
    op.create_table("preferencia_cliente_color",sa.Column("id_preferencia",sa.Integer(),sa.ForeignKey("preferencia_cliente.id_preferencia"),primary_key=True),sa.Column("id_color",sa.Integer(),sa.ForeignKey("color.id_color"),primary_key=True))
def downgrade() -> None:
    op.drop_table("preferencia_cliente_color"); op.drop_table("preferencia_cliente")
