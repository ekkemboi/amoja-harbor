from __future__ import annotations

import os
from pathlib import Path
from typing import ClassVar

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from app import create_app
from app.config import Config, normalize_database_url
from sqlalchemy import create_engine, text

from tests.factories import Factory

BASE_DIR = Path(__file__).resolve().parent.parent


def _test_database_url(tmp_dir: Path) -> str:
    raw = os.environ.get("TEST_DATABASE_URL")
    if raw:
        return normalize_database_url(raw)
    return f"sqlite:///{tmp_dir / 'amoja_harbor_test.db'}"


@pytest.fixture(scope="session")
def database_url(tmp_path_factory: pytest.TempPathFactory) -> str:
    """Point the suite at a throwaway SQLite file and migrate it."""
    url = _test_database_url(tmp_path_factory.mktemp("amoja-harbor-db"))

    # Fail early and clearly if an override points somewhere unusable.
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            connection.execute(text("select 1"))
    finally:
        engine.dispose()

    alembic_config = AlembicConfig(str(BASE_DIR / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(BASE_DIR / "migrations"))
    alembic_config.set_main_option("sqlalchemy.url", url)
    command.upgrade(alembic_config, "head")

    return url


@pytest.fixture(scope="session")
def app(database_url: str):
    class TestConfig(Config):
        TESTING = True
        WTF_CSRF_ENABLED = False
        SECRET_KEY = "test-only-key"
        SQLALCHEMY_DATABASE_URI = database_url
        SQLALCHEMY_ENGINE_OPTIONS: ClassVar[dict[str, object]] = {"pool_pre_ping": True}

    return create_app(TestConfig)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def factory(app):
    instance = Factory(app)
    yield instance
    instance.cleanup()
