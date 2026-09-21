"""Create private body profile storage metadata."""
from alembic import op
import sqlalchemy as sa

revision = "20260919_0020"
down_revision = "20260919_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "perfil_corporal",
        sa.Column("id_perfil_corporal", sa.Integer(), primary_key=True),
        sa.Column("id_usuario", sa.Integer(), sa.ForeignKey("usuario.id_usuario"), nullable=False, unique=True),
        sa.Column("consentimiento", sa.Boolean(), nullable=False),
        sa.Column("altura_cm", sa.Numeric(6, 2), nullable=True),
        sa.Column("peso_kg", sa.Numeric(6, 2), nullable=True),
        sa.Column("pecho_cm", sa.Numeric(6, 2), nullable=True),
        sa.Column("cintura_cm", sa.Numeric(6, 2), nullable=True),
        sa.Column("cadera_cm", sa.Numeric(6, 2), nullable=True),
        sa.Column("largo_pierna_cm", sa.Numeric(6, 2), nullable=True),
        sa.Column("ancho_hombros_cm", sa.Numeric(6, 2), nullable=True),
        sa.Column("foto_frontal", sa.String(500), nullable=True),
        sa.Column("foto_posterior", sa.String(500), nullable=True),
        sa.Column("foto_lateral_izquierda", sa.String(500), nullable=True),
        sa.Column("foto_lateral_derecha", sa.String(500), nullable=True),
    )
    op.create_index("ix_perfil_corporal_id_usuario", "perfil_corporal", ["id_usuario"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_perfil_corporal_id_usuario", table_name="perfil_corporal")
    op.drop_table("perfil_corporal")
