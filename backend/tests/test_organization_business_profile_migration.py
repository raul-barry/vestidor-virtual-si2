import importlib.util
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


MIGRATION_PATH = Path(__file__).parents[1] / "alembic" / "versions" / "20261103_0027_organization_business_profile.py"
spec = importlib.util.spec_from_file_location("organization_business_profile_migration", MIGRATION_PATH)
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


def _legacy_organization_db():
    engine = sa.create_engine("sqlite://")
    connection = engine.connect()
    connection.execute(sa.text("""
        CREATE TABLE organizacion (
            id_organizacion INTEGER PRIMARY KEY,
            nombre VARCHAR(150) NOT NULL UNIQUE,
            slug VARCHAR(160) NOT NULL UNIQUE,
            estado VARCHAR(30) NOT NULL
        )
    """))
    connection.execute(sa.text(
        "INSERT INTO organizacion VALUES (1, 'FashionStore', 'fashionstore', 'ACTIVA')"
    ))
    connection.commit()
    return engine, connection


def _run_migration(connection, operation):
    context = MigrationContext.configure(connection)
    with Operations.context(context):
        operation()


def test_upgrade_preserves_legacy_organization_and_leaves_new_fields_empty():
    engine, connection = _legacy_organization_db()
    _run_migration(connection, migration.upgrade)

    row = connection.execute(sa.text("SELECT * FROM organizacion WHERE id_organizacion=1")).mappings().one()
    assert (row["nombre"], row["slug"], row["estado"]) == ("FashionStore", "fashionstore", "ACTIVA")
    assert all(row[column] is None for column in migration.PROFILE_COLUMNS)
    assert "uq_organizacion_nit" in {index["name"] for index in sa.inspect(connection).get_indexes("organizacion")}

    _run_migration(connection, migration.downgrade)
    row = connection.execute(sa.text("SELECT * FROM organizacion WHERE id_organizacion=1")).mappings().one()
    assert dict(row) == {"id_organizacion": 1, "nombre": "FashionStore", "slug": "fashionstore", "estado": "ACTIVA"}
    connection.close()
    engine.dispose()


def test_downgrade_refuses_to_drop_business_data():
    engine, connection = _legacy_organization_db()
    _run_migration(connection, migration.upgrade)
    connection.execute(sa.text("UPDATE organizacion SET razon_social='Fashion Store SRL', nit='123456789' WHERE id_organizacion=1"))
    connection.commit()

    with pytest.raises(RuntimeError, match="exporte los datos empresariales"):
        _run_migration(connection, migration.downgrade)

    row = connection.execute(sa.text("SELECT razon_social, nit FROM organizacion WHERE id_organizacion=1")).one()
    assert row == ("Fashion Store SRL", "123456789")
    connection.close()
    engine.dispose()
