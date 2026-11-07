"""Allow platform administrator accounts to be global."""

from alembic import op
import sqlalchemy as sa


revision = "20261106_0037"
down_revision = "20261106_0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("usuario") as batch:
        batch.alter_column(
            "id_organizacion",
            existing_type=sa.Integer(),
            nullable=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    global_admins = bind.execute(sa.text(
        "SELECT COUNT(*) FROM usuario u JOIN rol r ON r.id_rol=u.id_rol "
        "WHERE u.id_organizacion IS NULL AND r.nombre='ADMINISTRADOR_PLATAFORMA'"
    )).scalar_one()
    if global_admins:
        raise RuntimeError("Downgrade bloqueado: reasigne o elimine los administradores globales antes de hacer id_organizacion NOT NULL")
    with op.batch_alter_table("usuario") as batch:
        batch.alter_column(
            "id_organizacion",
            existing_type=sa.Integer(),
            nullable=False,
        )
