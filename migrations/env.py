"""Alembic environment, wired to the app's own configuration and metadata."""

from __future__ import annotations

import os
from logging.config import fileConfig

import app.models  # noqa: F401  (registers every table on the metadata)
from alembic import context
from app.config import Config, normalize_database_url
from app.db import Base
from sqlalchemy import create_engine, pool

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url() -> str:
    """Prefer an explicit override so tests can migrate a throwaway database.

    Resolution order: the ALEMBIC_DATABASE_URL environment variable, then the
    ``sqlalchemy.url`` main option set programmatically, then the app config.
    """
    override = os.environ.get("ALEMBIC_DATABASE_URL") or config.get_main_option("sqlalchemy.url")
    return normalize_database_url(override) if override else Config.SQLALCHEMY_DATABASE_URI


def _configure(**kwargs) -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        **kwargs,
    )


def run_migrations_offline() -> None:
    _configure(literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(_database_url(), poolclass=pool.NullPool)
    try:
        with engine.connect() as connection:
            _configure(connection=connection)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
