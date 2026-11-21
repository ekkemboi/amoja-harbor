"""Database engine, declarative base, and per-request session handling."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from flask import Flask, current_app, g
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """Declarative base shared by every Amoja Harbor model."""


def _enable_sqlite_pragmas(engine: Engine) -> None:
    """Turn on foreign keys and sensible concurrency defaults for every connection.

    SQLite ignores foreign keys unless the pragma is set per connection, and the
    schema relies on ``ON DELETE CASCADE`` rather than ORM-only cascades.
    """

    @event.listens_for(engine, "connect")
    def _set_pragmas(dbapi_connection, connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()


def init_db(app: Flask) -> None:
    url = app.config["SQLALCHEMY_DATABASE_URI"]
    options = dict(app.config.get("SQLALCHEMY_ENGINE_OPTIONS") or {})

    if url.startswith("sqlite"):
        # Flask's threaded dev server may hand a pooled connection to another thread.
        connect_args = dict(options.get("connect_args") or {})
        connect_args.setdefault("check_same_thread", False)
        options["connect_args"] = connect_args

    engine = create_engine(url, echo=app.config.get("SQLALCHEMY_ECHO", False), **options)
    if url.startswith("sqlite"):
        _enable_sqlite_pragmas(engine)

    app.extensions["engine"] = engine
    app.extensions["session_factory"] = sessionmaker(bind=engine, expire_on_commit=False)

    @app.teardown_appcontext
    def _close_session(exception: BaseException | None) -> None:
        session = g.pop("db_session", None)
        if session is not None:
            session.close()


def get_session() -> Session:
    """Return the session bound to the current request/app context."""
    if "db_session" not in g:
        g.db_session = current_app.extensions["session_factory"]()
    return g.db_session


@contextmanager
def session_scope() -> Iterator[Session]:
    """Transactional session for scripts, CLI commands, and background work."""
    session: Session = current_app.extensions["session_factory"]()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
