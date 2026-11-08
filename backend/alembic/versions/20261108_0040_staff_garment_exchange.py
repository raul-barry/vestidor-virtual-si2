"""Allow staff exchanges for walk-in POS sales without a customer record."""
from alembic import op
import sqlalchemy as sa

revision = "20261108_0040"
down_revision = "20261107_0039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("garment_exchange", "customer_id", nullable=True)


def downgrade() -> None:
    # Existing POS walk-in exchange rows cannot satisfy the former NOT NULL rule.
    bind = op.get_bind()
    walk_in_rows = bind.execute(sa.text(
        "SELECT count(*) FROM garment_exchange WHERE customer_id IS NULL"
    )).scalar_one()
    if walk_in_rows:
        raise RuntimeError("Cannot downgrade while garment exchanges without a customer exist")
    op.alter_column("garment_exchange", "customer_id", nullable=False)
