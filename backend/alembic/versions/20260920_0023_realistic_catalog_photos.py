"""Use realistic raster photos for seeded catalogue products.

Revision ID: 20260920_0023
Revises: 20260920_0022
"""

from alembic import op


revision = "20260920_0023"
down_revision = "20260920_0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Keep the old SVG records for rollback/history, but stop selecting them as
    # active catalogue images. The seed and the new resources use the same
    # stable product-index mapping as the original five products.
    op.execute(
        "UPDATE recurso_virtual SET estado = 'INACTIVO' "
        "WHERE tipo_recurso = 'imagen' AND url_archivo LIKE '/api/assets/fitting/prenda-%.svg'"
    )
    op.execute(
        "INSERT INTO recurso_virtual (id_producto, tipo_recurso, url_archivo, estado) "
        "SELECT id_producto, 'imagen', '/api/assets/catalog/catalog-prenda-' "
        "|| substring(url_archivo from 'prenda-([0-9]+)') || '.png', 'ACTIVO' "
        "FROM recurso_virtual "
        "WHERE tipo_recurso = 'imagen' AND url_archivo LIKE '/api/assets/fitting/prenda-%.svg' "
        "ON CONFLICT (id_producto, url_archivo) DO UPDATE SET estado = 'ACTIVO'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE recurso_virtual SET estado = 'INACTIVO' "
        "WHERE tipo_recurso = 'imagen' AND url_archivo LIKE '/api/assets/catalog/catalog-prenda-%.png'"
    )
    op.execute(
        "UPDATE recurso_virtual SET estado = 'ACTIVO' "
        "WHERE tipo_recurso = 'imagen' AND url_archivo LIKE '/api/assets/fitting/prenda-%.svg'"
    )
