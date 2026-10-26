"""Database engine, declarative base, and per-request session handling."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from flask import Flask, current_app, g
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """Declarative base shared by every Harbor model."""


def init_db(app: Flask) -> None:
    engine = create_engine(
        app.config["SQLALCHEMY_DATABASE_URI"],
        echo=app.config.get("SQLALCHEMY_ECHO", False),
        **app.config["SQLALCHEMY_ENGINE_OPTIONS"],
    )
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
