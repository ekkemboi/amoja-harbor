"""Sign up, sign in, sign out."""

from __future__ import annotations

from flask import Blueprint, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy.exc import IntegrityError

from ..accounts import AccountError, authenticate, create_account
from ..db import get_session

bp = Blueprint("auth", __name__)


def _safe_next(target: str | None) -> str:
    """Only follow same-site relative paths after login."""
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return url_for("start.index")


@bp.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("start.index"))

    form = {"name": "", "email": "", "org_name": ""}
    errors: list[str] = []

    if request.method == "POST":
        form = {
            "name": request.form.get("name", ""),
            "email": request.form.get("email", ""),
            "org_name": request.form.get("org_name", ""),
        }
        try:
            user, org = create_account(
                get_session(),
                name=form["name"],
                email=form["email"],
                password=request.form.get("password", ""),
                org_name=form["org_name"],
            )
        except AccountError as exc:
            errors.append(str(exc))
        except IntegrityError:
            get_session().rollback()
            errors.append("That email is already registered.")
        else:
            login_user(user)
            session.permanent = True
            return redirect(url_for("orgs.home", org_slug=org.slug))

    return render_template("auth/signup.html", form=form, errors=errors), (400 if errors else 200)


@bp.route("/signin", methods=["GET", "POST"])
def signin():
    if current_user.is_authenticated:
        return redirect(url_for("start.index"))

    email = ""
    error: str | None = None

    if request.method == "POST":
        email = request.form.get("email", "")
        user = authenticate(
            get_session(),
            email=email,
            password=request.form.get("password", ""),
        )
        if user is None:
            error = "Email or password is incorrect."
        else:
            login_user(user)
            session.permanent = True
            return redirect(_safe_next(request.args.get("next")))

    return render_template("auth/signin.html", email=email, error=error), (401 if error else 200)


@bp.post("/signout")
@login_required
def signout():
    logout_user()
    session.clear()
    return redirect(url_for("public.index"))
