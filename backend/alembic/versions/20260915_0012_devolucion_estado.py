"""Add return workflow status."""
from alembic import op
import sqlalchemy as sa

revision = "20260915_0012"
down_revision = "20260914_0011"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("devolucion") as batch:
        batch.add_column(sa.Column("estado", sa.String(30), nullable=False, server_default="COMPLETADA"))


def downgrade():
    with op.batch_alter_table("devolucion") as batch:
        batch.drop_column("estado")
