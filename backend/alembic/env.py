import os
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool
from dotenv import dotenv_values

import app.models  # noqa: F401  # Imports future models registered by the package.
from app.models.base import Base

config = context.config
env_file = Path(config.config_file_name or "alembic.ini").resolve().parent / ".env"
database_url = (
    os.getenv("DATABASE_URL")
    or dotenv_values(env_file).get("DATABASE_URL")
    or config.get_main_option("sqlalchemy.url")
)
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
config.set_main_option("sqlalchemy.url", database_url)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(config.get_section(config.config_ini_section), prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
