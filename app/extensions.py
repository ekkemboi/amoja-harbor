"""Shared Flask extension instances (initialized in the app factory)."""

from __future__ import annotations

from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

login_manager = LoginManager()
login_manager.login_view = "auth.signin"
login_manager.login_message = None
login_manager.session_protection = "strong"

csrf = CSRFProtect()
