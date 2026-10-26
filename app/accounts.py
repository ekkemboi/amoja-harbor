"""Account and workspace creation — the business rules behind the auth views."""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Membership, Organization, Role, User
from .security import hash_password, verify_password

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 10


class AccountError(ValueError):
    """Validation failure whose message is safe to show to the user."""


def normalize_email(email: str) -> str:
    return email.strip().lower()


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:40] or "workspace"


def unique_org_slug(db: Session, name: str) -> str:
    base = slugify(name)
    slug = base
    suffix = 2
    while db.scalar(select(Organization.id).where(Organization.slug == slug)) is not None:
        slug = f"{base}-{suffix}"[:48]
        suffix += 1
    return slug


def create_account(
    db: Session,
    *,
    name: str,
    email: str,
    password: str,
    org_name: str,
) -> tuple[User, Organization]:
    """Create a user and their first workspace, with the user as owner."""
    name = name.strip()
    email = normalize_email(email)
    org_name = org_name.strip()

    if len(name) < 2:
        raise AccountError("Enter your name.")
    if not EMAIL_PATTERN.match(email):
        raise AccountError("Enter a valid email address.")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AccountError(f"Use at least {MIN_PASSWORD_LENGTH} characters for your password.")
    if len(org_name) < 2:
        raise AccountError("Enter a workspace name.")
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise AccountError("That email is already registered.")

    user = User(name=name, email=email, password_hash=hash_password(password))
    org = Organization(name=org_name, slug=unique_org_slug(db, org_name))
    db.add_all([user, org])
    db.flush()
    db.add(Membership(org_id=org.id, user_id=user.id, role=Role.OWNER))
    db.commit()
    return user, org


def create_workspace(db: Session, user: User, name: str) -> Organization:
    name = name.strip()
    if len(name) < 2:
        raise AccountError("Enter a workspace name.")

    org = Organization(name=name, slug=unique_org_slug(db, name))
    db.add(org)
    db.flush()
    db.add(Membership(org_id=org.id, user_id=user.id, role=Role.OWNER))
    db.commit()
    return org


def authenticate(db: Session, *, email: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.email == normalize_email(email)))
    if user is None:
        # Still burn a hash check so a missing account is not faster than a wrong password.
        verify_password(None, password)
        return None
    if not verify_password(user.password_hash, password):
        return None
    return user
