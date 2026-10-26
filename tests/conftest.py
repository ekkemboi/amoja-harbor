from __future__ import annotations

import pytest
from app import create_app
from app.config import Config

from tests.factories import Factory


class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-only-key"


@pytest.fixture(scope="session")
def app():
    return create_app(TestConfig)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def factory(app):
    instance = Factory(app)
    yield instance
    instance.cleanup()
