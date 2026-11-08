"""Enable the customer loyalty capability for Plan Glamour only."""
from alembic import op
import sqlalchemy as sa


revision = "20261108_0041"
down_revision = "20261108_0040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("""
        UPDATE plan_caracteristica AS feature
        SET habilitada = TRUE
        FROM plan
        WHERE feature.plan_id = plan.id_plan
          AND plan.codigo = 'GLAMOUR'
          AND feature.codigo = 'fidelizacion_clientes'
    """))


def downgrade() -> None:
    op.execute(sa.text("""
        UPDATE plan_caracteristica AS feature
        SET habilitada = FALSE
        FROM plan
        WHERE feature.plan_id = plan.id_plan
          AND plan.codigo = 'GLAMOUR'
          AND feature.codigo = 'fidelizacion_clientes'
    """))
