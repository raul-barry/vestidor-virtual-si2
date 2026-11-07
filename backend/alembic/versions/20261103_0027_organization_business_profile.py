"""Add optional business profile fields to organizations."""

from alembic import op
import sqlalchemy as sa


revision = "20261103_0027"
down_revision = "20261103_0026"
branch_labels = None
depends_on = None


PROFILE_COLUMNS = (
    "razon_social",
    "nit",
    "correo_contacto",
    "telefono_contacto",
    "direccion",
    "logo_url",
    "fecha_creacion",
    "fecha_actualizacion",
)


def upgrade() -> None:
    op.add_column("organizacion", sa.Column("razon_social", sa.String(200), nullable=True))
    op.add_column("organizacion", sa.Column("nit", sa.String(20), nullable=True))
    op.add_column("organizacion", sa.Column("correo_contacto", sa.String(254), nullable=True))
    op.add_column("organizacion", sa.Column("telefono_contacto", sa.String(30), nullable=True))
    op.add_column("organizacion", sa.Column("direccion", sa.String(255), nullable=True))
    op.add_column("organizacion", sa.Column("logo_url", sa.String(2048), nullable=True))
    op.add_column("organizacion", sa.Column("fecha_creacion", sa.DateTime(timezone=True), nullable=True))
    op.add_column("organizacion", sa.Column("fecha_actualizacion", sa.DateTime(timezone=True), nullable=True))
    op.create_index("uq_organizacion_nit", "organizacion", ["nit"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    populated = bind.execute(sa.text(
        "SELECT COUNT(*) FROM organizacion WHERE "
        + " OR ".join(f"{column} IS NOT NULL" for column in PROFILE_COLUMNS)
    )).scalar_one()
    if populated:
        raise RuntimeError(
            "Downgrade bloqueado: exporte los datos empresariales añadidos antes de eliminar las columnas"
        )
    op.drop_index("uq_organizacion_nit", table_name="organizacion")
    for column in reversed(PROFILE_COLUMNS):
        op.drop_column("organizacion", column)
