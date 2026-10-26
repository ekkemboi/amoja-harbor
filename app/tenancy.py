"""Organization scoping and role enforcement.

Two rules hold everywhere:

1. A route under ``/app/<org_slug>/...`` only ever sees data for that org.
2. The server rejects unauthorized actions even when the UI hides the control.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from flask import abort, g
from sqlalchemy import select

from .db import get_session
from .models import Membership, Organization, Role

F = TypeVar("F", bound=Callable[..., Any])


def load_org(slug: str) -> Organization:
    org = get_session().scalar(select(Organization).where(Organization.slug == slug))
    if org is None:
        abort(404)
    return org


def load_membership(org: Organization, user) -> Membership | None:
    if not getattr(user, "is_authenticated", False):
        return None
    return get_session().scalar(
        select(Membership).where(
            Membership.org_id == org.id,
            Membership.user_id == user.id,
        )
    )


def current_org() -> Organization:
    org = g.get("org")
    if org is None:
        abort(404)
    return org


def current_membership() -> Membership:
    membership = g.get("membership")
    if membership is None:
        abort(404)
    return membership


def requires_role(minimum: Role) -> Callable[[F], F]:
    """Reject the request unless the caller's role is at least ``minimum``."""

    def decorator(view: F) -> F:
        @wraps(view)
        def wrapper(*args: Any, **kwargs: Any):
            membership = g.get("membership")
            if membership is None:
                abort(404)
            if not membership.role.allows(minimum):
                abort(403)
            return view(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator
