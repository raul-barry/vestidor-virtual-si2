"""Add dedicated raster resources for photo virtual try-on.

Revision ID: 20260920_0022
Revises: 20260920_0021
"""

from alembic import op


revision = "20260920_0022"
down_revision = "20260920_0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PostgreSQL gives the unnamed original check this deterministic name.
    op.execute("ALTER TABLE recurso_virtual DROP CONSTRAINT recurso_virtual_tipo_recurso_check")
    op.execute(
        "ALTER TABLE recurso_virtual ADD CONSTRAINT ck_recurso_virtual_tipo_recurso "
        "CHECK (tipo_recurso IN ('imagen', 'modelo_3d', 'tryon'))"
    )
    # Preserve each SVG catalogue resource and add a separate PNG only for
    # the seeded product set. ON CONFLICT makes this safe on existing data.
    op.execute(
        "INSERT INTO recurso_virtual (id_producto, tipo_recurso, url_archivo, estado) "
        "SELECT id_producto, 'tryon', replace(replace(url_archivo, '/fitting/', '/tryon/'), '.svg', '.png'), estado "
        "FROM recurso_virtual "
        "WHERE tipo_recurso = 'imagen' AND url_archivo LIKE '/api/assets/fitting/prenda-%.svg' "
        "ON CONFLICT (id_producto, url_archivo) DO NOTHING"
    )


def downgrade() -> None:
    op.execute("DELETE FROM recurso_virtual WHERE tipo_recurso = 'tryon' AND url_archivo LIKE '/api/assets/tryon/prenda-%.png'")
    op.execute("ALTER TABLE recurso_virtual DROP CONSTRAINT ck_recurso_virtual_tipo_recurso")
    op.execute(
        "ALTER TABLE recurso_virtual ADD CONSTRAINT recurso_virtual_tipo_recurso_check "
        "CHECK (tipo_recurso IN ('imagen', 'modelo_3d'))"
    )
