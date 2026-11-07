"""Add public organization slugs and the platform administrator role."""

import re
import unicodedata

from alembic import op
import sqlalchemy as sa


revision = "20261103_0026"
down_revision = "20261103_0025"
branch_labels = None
depends_on = None


def _slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-") or "empresa"


def upgrade() -> None:
    op.add_column("organizacion", sa.Column("slug", sa.String(160), nullable=True))
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id_organizacion, nombre FROM organizacion ORDER BY id_organizacion")).all()
    used = set()
    for org_id, name in rows:
        base = _slug(name)
        value, suffix = base, 2
        while value in used:
            value = f"{base}-{suffix}"
            suffix += 1
        used.add(value)
        bind.execute(sa.text("UPDATE organizacion SET slug = :slug WHERE id_organizacion = :id"), {"slug": value, "id": org_id})
    with op.batch_alter_table("organizacion") as batch:
        batch.alter_column("slug", existing_type=sa.String(160), nullable=False)
        batch.create_unique_constraint("uq_organizacion_slug", ["slug"])

    bind.execute(sa.text("""INSERT INTO rol (nombre, descripcion, estado)
        SELECT 'ADMINISTRADOR_PLATAFORMA', 'Operaciones globales de plataforma', 'ACTIVO'
        WHERE NOT EXISTS (SELECT 1 FROM rol WHERE nombre = 'ADMINISTRADOR_PLATAFORMA')"""))


def downgrade() -> None:
    bind = op.get_bind()
    count = bind.execute(sa.text("SELECT COUNT(*) FROM usuario u JOIN rol r ON r.id_rol=u.id_rol WHERE r.nombre='ADMINISTRADOR_PLATAFORMA'")).scalar_one()
    if count:
        raise RuntimeError("Downgrade bloqueado: reasigne los usuarios de plataforma antes de quitar el rol")
    bind.execute(sa.text("DELETE FROM rol_permiso WHERE id_rol IN (SELECT id_rol FROM rol WHERE nombre='ADMINISTRADOR_PLATAFORMA')"))
    bind.execute(sa.text("DELETE FROM rol WHERE nombre = 'ADMINISTRADOR_PLATAFORMA'"))
    with op.batch_alter_table("organizacion") as batch:
        batch.drop_constraint("uq_organizacion_slug", type_="unique")
        batch.drop_column("slug")
