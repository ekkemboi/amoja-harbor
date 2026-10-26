"""Application configuration, loaded from the environment."""

from __future__ import annotations

import os
from pathlib import Path
from typing import ClassVar

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Neon writes .env.local; a conventional Flask project uses .env. Support both,
# with real environment variables always taking precedence.
load_dotenv(BASE_DIR / ".env.local")
load_dotenv(BASE_DIR / ".env")


def _database_url() -> str:
    """Build the SQLAlchemy URL for the direct (non-pooler) endpoint.

    A long-lived gunicorn process keeps its own connection pool, so it talks to
    Postgres directly instead of through PgBouncer. Serverless callers should
    use DATABASE_URL (the pooled endpoint) instead.
    """
    raw = os.environ.get("DATABASE_URL_UNPOOLED") or os.environ.get("DATABASE_URL")
    if not raw:
        raise RuntimeError(
            "No database URL found. Run `neon env pull --file .env`, "
            "or copy .env.example to .env and fill it in."
        )
    for prefix in ("postgresql://", "postgres://"):
        if raw.startswith(prefix):
            return raw.replace(prefix, "postgresql+psycopg://", 1)
    return raw


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-insecure-key")
    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_ENGINE_OPTIONS: ClassVar[dict[str, object]] = {
        "pool_pre_ping": True,
        "pool_size": 5,
        "max_overflow": 10,
        "pool_recycle": 300,
    }
    SQLALCHEMY_ECHO = os.environ.get("SQLALCHEMY_ECHO") == "1"
