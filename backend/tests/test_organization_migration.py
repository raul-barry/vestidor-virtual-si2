import importlib.util
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


MIGRATION_PATH = Path(__file__).parents[1] / "alembic" / "versions" / "20261103_0025_organization_ownership.py"
spec = importlib.util.spec_from_file_location("organization_ownership_migration", MIGRATION_PATH)
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


def _legacy_connection():
    engine = sa.create_engine("sqlite://")
    connection = engine.connect()
    connection.exec_driver_sql("PRAGMA foreign_keys=ON")
    for table, constraint in (
        ("usuario", None),
        ("sucursal", "sucursal_nombre_key"),
        ("producto", None),
        ("proveedor", "proveedor_nombre_key"),
        ("coleccion", "coleccion_nombre_key"),
    ):
        constraints = f", CONSTRAINT {constraint} UNIQUE (nombre)" if constraint else ""
        connection.execute(sa.text(
            f"CREATE TABLE {table} (id INTEGER PRIMARY KEY, nombre VARCHAR(150) NOT NULL{constraints})"
        ))
        connection.execute(sa.text(f"INSERT INTO {table} (id, nombre) VALUES (1, 'legacy-{table}')"))
    connection.commit()
    return engine, connection


def test_upgrade_backfills_legacy_rows_and_safe_downgrade():
    engine, connection = _legacy_connection()
    context = MigrationContext.configure(connection)
    with Operations.context(context):
        migration.upgrade()

    for table in migration.OWNED_TABLES:
        assert connection.execute(sa.text(f"SELECT id_organizacion FROM {table} WHERE id = 1")).scalar_one() == 1
    assert connection.execute(sa.text("SELECT nombre FROM organizacion WHERE id_organizacion = 1")).scalar_one() == "FashionStore"

    with Operations.context(context):
        migration.downgrade()
    assert "organizacion" not in sa.inspect(connection).get_table_names()
    for table in migration.OWNED_TABLES:
        assert "id_organizacion" not in {column["name"] for column in sa.inspect(connection).get_columns(table)}
    connection.close()
    engine.dispose()


def test_downgrade_refuses_to_drop_additional_organizations():
    engine, connection = _legacy_connection()
    context = MigrationContext.configure(connection)
    with Operations.context(context):
        migration.upgrade()
    connection.execute(sa.text("INSERT INTO organizacion (id_organizacion, nombre, estado) VALUES (2, 'Otra', 'ACTIVA')"))
    connection.commit()

    with Operations.context(context), pytest.raises(RuntimeError, match="organizaciones adicionales"):
        migration.downgrade()
    assert "id_organizacion" in {column["name"] for column in sa.inspect(connection).get_columns("usuario")}
    connection.close()
    engine.dispose()


def test_slug_and_platform_role_migration_is_reversible():
    path = MIGRATION_PATH.with_name("20261103_0026_organization_slug_and_platform_role.py")
    slug_spec = importlib.util.spec_from_file_location("organization_slug_migration", path)
    slug_migration = importlib.util.module_from_spec(slug_spec)
    slug_spec.loader.exec_module(slug_migration)
    engine = sa.create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(sa.text("CREATE TABLE organizacion (id_organizacion INTEGER PRIMARY KEY, nombre VARCHAR(150) NOT NULL UNIQUE, estado VARCHAR(30) NOT NULL)"))
        connection.execute(sa.text("INSERT INTO organizacion VALUES (1, 'FashionStore', 'ACTIVA'), (2, 'Elegance Boutique', 'ACTIVA')"))
        connection.execute(sa.text("CREATE TABLE rol (id_rol INTEGER PRIMARY KEY, nombre VARCHAR(100) UNIQUE, descripcion VARCHAR(255), estado VARCHAR(30))"))
        connection.execute(sa.text("INSERT INTO rol VALUES (1, 'ADMINISTRADOR', '', 'ACTIVO')"))
        connection.execute(sa.text("CREATE TABLE rol_permiso (id_rol INTEGER NOT NULL, id_permiso INTEGER NOT NULL, PRIMARY KEY (id_rol, id_permiso))"))
        connection.execute(sa.text("CREATE TABLE usuario (id_usuario INTEGER PRIMARY KEY, id_rol INTEGER NOT NULL)"))
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            slug_migration.upgrade()
        slugs = connection.execute(sa.text("SELECT slug FROM organizacion ORDER BY id_organizacion")).scalars().all()
        assert slugs == ["fashionstore", "elegance-boutique"]
        assert connection.execute(sa.text("SELECT COUNT(*) FROM rol WHERE nombre='ADMINISTRADOR_PLATAFORMA'")).scalar_one() == 1
        with Operations.context(context):
            slug_migration.downgrade()
        assert "slug" not in {column["name"] for column in sa.inspect(connection).get_columns("organizacion")}
    engine.dispose()
