"""Canonicalize persisted payment states.

Revision ID: 20260920_0021
Revises: 20260919_0020
"""

from alembic import op


revision = "20260920_0021"
down_revision = "20260919_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Keep this data migration explicit: APROBADO/RECHAZADO were the former
    # public contract, while the payment API now consistently uses
    # PAGADO/FALLIDO. The column has no database enum/check constraint.
    op.execute("UPDATE pago SET estado = 'PAGADO' WHERE estado = 'APROBADO'")
    op.execute("UPDATE pago SET estado = 'FALLIDO' WHERE estado = 'RECHAZADO'")


def downgrade() -> None:
    op.execute("UPDATE pago SET estado = 'APROBADO' WHERE estado = 'PAGADO'")
    op.execute("UPDATE pago SET estado = 'RECHAZADO' WHERE estado = 'FALLIDO'")
