"""Add organization ownership to tenant-owned master data."""

from alembic import op
import sqlalchemy as sa


revision = "20261103_0025"
down_revision = "20260929_0024"
branch_labels = None
depends_on = None


OWNED_TABLES = ("usuario", "sucursal", "producto", "proveedor", "coleccion")
OLD_UNIQUES = {
    "sucursal": ("sucursal_nombre_key", "uq_sucursal_organizacion_nombre"),
    "proveedor": ("proveedor_nombre_key", "uq_proveedor_organizacion_nombre"),
    "coleccion": ("coleccion_nombre_key", "uq_coleccion_organizacion_nombre"),
}


def upgrade() -> None:
    op.create_table(
        "organizacion",
        sa.Column("id_organizacion", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(150), nullable=False),
        sa.Column("estado", sa.String(30), nullable=False, server_default="ACTIVA"),
        sa.UniqueConstraint("nombre", name="uq_organizacion_nombre"),
    )
    bind = op.get_bind()
    organization_id = bind.execute(
        sa.text("SELECT id_organizacion FROM organizacion WHERE nombre = :name"),
        {"name": "FashionStore"},
    ).scalar_one_or_none()
    if organization_id is None:
        organization_id = 1
        bind.execute(
            sa.text("INSERT INTO organizacion (id_organizacion, nombre, estado) VALUES (:id, :name, :state)"),
            {"id": organization_id, "name": "FashionStore", "state": "ACTIVA"},
        )

    for table in OWNED_TABLES:
        op.add_column(table, sa.Column("id_organizacion", sa.Integer(), nullable=True))
        bind.execute(
            sa.text(f"UPDATE {table} SET id_organizacion = :organization_id WHERE id_organizacion IS NULL"),
            {"organization_id": organization_id},
        )
        with op.batch_alter_table(table) as batch:
            batch.alter_column("id_organizacion", existing_type=sa.Integer(), nullable=False)
            batch.create_foreign_key(
                f"fk_{table}_organizacion", "organizacion", ["id_organizacion"], ["id_organizacion"]
            )
        op.create_index(f"ix_{table}_id_organizacion", table, ["id_organizacion"])

    for table, (old_name, new_name) in OLD_UNIQUES.items():
        with op.batch_alter_table(table) as batch:
            batch.drop_constraint(old_name, type_="unique")
            batch.create_unique_constraint(new_name, ["id_organizacion", "nombre"])


def downgrade() -> None:
    bind = op.get_bind()
    other_orgs = bind.execute(
        sa.text("SELECT COUNT(*) FROM organizacion WHERE id_organizacion <> 1")
    ).scalar_one()
    if other_orgs:
        raise RuntimeError("Downgrade bloqueado: existen organizaciones adicionales; reasigne o exporte sus datos primero")

    for table, (old_name, new_name) in OLD_UNIQUES.items():
        with op.batch_alter_table(table) as batch:
            batch.drop_constraint(new_name, type_="unique")
            batch.create_unique_constraint(old_name, ["nombre"])

    for table in reversed(OWNED_TABLES):
        op.drop_index(f"ix_{table}_id_organizacion", table_name=table)
        with op.batch_alter_table(table) as batch:
            batch.drop_constraint(f"fk_{table}_organizacion", type_="foreignkey")
            batch.drop_column("id_organizacion")
    op.drop_table("organizacion")
