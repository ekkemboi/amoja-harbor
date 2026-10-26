"""Unauthenticated routes: landing page and health check."""

from __future__ import annotations

from flask import Blueprint, render_template
from sqlalchemy import text

from ..db import get_session

bp = Blueprint("public", __name__)


@bp.get("/")
def index():
    return render_template("public/landing.html")


@bp.get("/healthz")
def healthz():
    try:
        get_session().execute(text("select 1"))
    except Exception as exc:  # surfaced to operators, not users
        return {
            "status": "degraded",
            "database": type(exc).__name__,
        }, 503
    return {"status": "ok", "database": "ok"}, 200
