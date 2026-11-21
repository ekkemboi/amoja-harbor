"""Application configuration, loaded from the environment."""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path
from typing import ClassVar

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
INSTANCE_DIR = BASE_DIR / "instance"
DEFAULT_DATABASE_PATH = INSTANCE_DIR / "amoja_harbor.db"

# .env.local wins over .env; real environment variables win over both.
load_dotenv(BASE_DIR / ".env.local")
load_dotenv(BASE_DIR / ".env")


def normalize_database_url(raw: str) -> str:
    """Make a relative SQLite path absolute so every process agrees on the file."""
    raw = raw.strip()
    prefix = "sqlite:///"
    if raw.startswith(prefix):
        path = raw[len(prefix) :]
        if path and path != ":memory:" and not Path(path).is_absolute():
            return f"{prefix}{(BASE_DIR / path).resolve()}"
    return raw


def _ensure_sqlite_parent(url: str) -> None:
    """Create the directory that will hold a file-backed SQLite database."""
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        return
    path = url[len(prefix) :]
    if path and path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)


def _database_url() -> str:
    """Use DATABASE_URL when provided, otherwise the local SQLite file."""
    raw = os.environ.get("DATABASE_URL")
    url = normalize_database_url(raw) if raw else f"sqlite:///{DEFAULT_DATABASE_PATH}"
    _ensure_sqlite_parent(url)
    return url


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-insecure-key")
    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_ENGINE_OPTIONS: ClassVar[dict[str, object]] = {"pool_pre_ping": True}
    SQLALCHEMY_ECHO = os.environ.get("SQLALCHEMY_ECHO") == "1"

    # Sessions live in SQLite (see app/session.py); these control the cookie.
    SESSION_COOKIE_NAME = "amoja_harbor_session"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # Enable in production, where the app is served over HTTPS.
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE") == "1"
    PERMANENT_SESSION_LIFETIME = timedelta(days=14)

    WTF_CSRF_TIME_LIMIT = None
