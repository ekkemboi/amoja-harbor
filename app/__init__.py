"""Harbor application factory."""

from __future__ import annotations

from flask import Flask

from .config import Config
from .db import init_db


def create_app(config_object: type = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_object)

    init_db(app)

    from .blueprints.public import bp as public_bp

    app.register_blueprint(public_bp)

    return app
