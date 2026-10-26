"""Org-scoped routes. Everything under /app/<org_slug>/ is tenant-isolated."""

from __future__ import annotations

from flask import Blueprint, abort, g, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func, select

from ..accounts import AccountError, create_workspace
from ..db import get_session
from ..extensions import login_manager
from ..models import Membership, Organization, Role
from ..tenancy import load_membership, load_org, requires_role

bp = Blueprint("orgs", __name__, url_prefix="/app/<org_slug>")
start_bp = Blueprint("start", __name__)


# --------------------------------------------------------------------------- #
# Tenant resolution
# --------------------------------------------------------------------------- #


@bp.url_value_preprocessor
def _pull_org(endpoint: str | None, values: dict | None) -> None:
    slug = (values or {}).pop("org_slug", None)
    if slug is not None:
        g.org = load_org(slug)


@bp.before_request
def _require_membership():
    if g.get("org") is None:
        abort(404)
    if not current_user.is_authenticated:
        return login_manager.unauthorized()

    membership = load_membership(g.org, current_user)
    if membership is None:
        # 404 rather than 403: do not confirm that another org exists.
        abort(404)
    g.membership = membership
    return None


# --------------------------------------------------------------------------- #
# Views
# --------------------------------------------------------------------------- #


@bp.get("/")
def home():
    db = get_session()
    members = db.scalars(
        select(Membership).where(Membership.org_id == g.org.id).order_by(Membership.created_at)
    ).all()

    return render_template(
        "orgs/home.html",
        org=g.org,
        membership=g.membership,
        members=members,
        Role=Role,
    )


@bp.post("/members/<uuid:membership_id>/role")
@requires_role(Role.ADMIN)
def update_member_role(membership_id):
    db = get_session()
    target = db.scalar(
        select(Membership).where(
            Membership.id == membership_id,
            Membership.org_id == g.org.id,
        )
    )
    if target is None:
        abort(404)

    try:
        new_role = Role(request.form.get("role", ""))
    except ValueError:
        abort(400)

    actor = g.membership
    if target.user_id == current_user.id:
        abort(400, "You cannot change your own role.")
    # Never touch, or grant, a role above your own.
    if target.role.rank > actor.role.rank or new_role.rank > actor.role.rank:
        abort(403)

    target.role = new_role
    db.commit()
    return redirect(url_for("orgs.home", org_slug=g.org.slug))


@bp.post("/members/<uuid:membership_id>/remove")
@requires_role(Role.ADMIN)
def remove_member(membership_id):
    db = get_session()
    target = db.scalar(
        select(Membership).where(
            Membership.id == membership_id,
            Membership.org_id == g.org.id,
        )
    )
    if target is None:
        abort(404)

    actor = g.membership
    if target.user_id == current_user.id:
        abort(400, "You cannot remove yourself.")
    if target.role.rank > actor.role.rank:
        abort(403)

    if target.role is Role.OWNER:
        owners = db.scalar(
            select(func.count())
            .select_from(Membership)
            .where(Membership.org_id == g.org.id, Membership.role == Role.OWNER)
        )
        if (owners or 0) <= 1:
            abort(400, "A workspace must keep at least one owner.")

    db.delete(target)
    db.commit()
    return redirect(url_for("orgs.home", org_slug=g.org.slug))


# --------------------------------------------------------------------------- #
# Entry point: pick a workspace or create the first one
# --------------------------------------------------------------------------- #


@start_bp.get("/app")
@login_required
def index():
    org = get_session().scalar(
        select(Organization)
        .join(Membership, Membership.org_id == Organization.id)
        .where(Membership.user_id == current_user.id)
        .order_by(Organization.created_at)
    )
    if org is not None:
        return redirect(url_for("orgs.home", org_slug=org.slug))

    return render_template("orgs/empty.html")


@start_bp.post("/app/new")
@login_required
def create():
    try:
        org = create_workspace(get_session(), current_user, request.form.get("name", ""))
    except AccountError as exc:
        abort(400, str(exc))
    return redirect(url_for("orgs.home", org_slug=org.slug))
