"""Amoja Harbor application factory."""

from __future__ import annotations

import uuid

from flask import Flask

from .config import Config
from .db import get_session, init_db
from .extensions import csrf, login_manager
from .models import User
from .session import DatabaseSessionInterface


def create_app(config_object: type = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_object)

    init_db(app)
    app.session_interface = DatabaseSessionInterface(
        cookie_name=app.config["SESSION_COOKIE_NAME"],
        lifetime=app.config["PERMANENT_SESSION_LIFETIME"],
    )
    login_manager.init_app(app)
    csrf.init_app(app)

    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        try:
            uid = uuid.UUID(user_id)
        except (TypeError, ValueError):
            return None
        return get_session().get(User, uid)

    from .blueprints.auth import bp as auth_bp
    from .blueprints.orgs import bp as orgs_bp
    from .blueprints.orgs import start_bp
    from .blueprints.public import bp as public_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(start_bp)
    app.register_blueprint(orgs_bp)

    @app.cli.command("prune-sessions")
    def prune_sessions() -> None:
        """Delete sessions that have passed their expiry."""
        removed = DatabaseSessionInterface.prune()
        print(f"Removed {removed} expired session(s).")

    return app
