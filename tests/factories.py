"""Row factories for tests, plus teardown so the dev database stays clean."""

from __future__ import annotations

import uuid

from app.models import Membership, Organization, Role, User
from app.security import hash_password
from sqlalchemy import delete, select

PASSWORD = "correct-horse-battery-staple"


def signin(client, email: str, password: str = PASSWORD):
    return client.post("/signin", data={"email": email, "password": password})


class Factory:
    def __init__(self, app) -> None:
        self.app = app
        self.emails: list[str] = []

    def _db(self):
        return self.app.extensions["session_factory"]()

    def email(self) -> str:
        email = f"test-{uuid.uuid4().hex[:12]}@example.test"
        self.emails.append(email)
        return email

    def user(self, *, name: str = "Test User", email: str | None = None) -> User:
        email = email or self.email()
        db = self._db()
        try:
            user = User(name=name, email=email, password_hash=hash_password(PASSWORD))
            db.add(user)
            db.commit()
            return user
        finally:
            db.close()

    def org(self, *, owner: User, name: str | None = None) -> Organization:
        db = self._db()
        try:
            org = Organization(name=name or "Test Org", slug=f"test-{uuid.uuid4().hex[:10]}")
            db.add(org)
            db.flush()
            db.add(Membership(org_id=org.id, user_id=owner.id, role=Role.OWNER))
            db.commit()
            return org
        finally:
            db.close()

    def member(self, org: Organization, user: User, role: Role) -> Membership:
        db = self._db()
        try:
            membership = Membership(org_id=org.id, user_id=user.id, role=role)
            db.add(membership)
            db.commit()
            return membership
        finally:
            db.close()

    def cleanup(self) -> None:
        if not self.emails:
            return
        db = self._db()
        try:
            user_ids = list(db.scalars(select(User.id).where(User.email.in_(self.emails))))
            if not user_ids:
                return
            org_ids = list(
                db.scalars(select(Membership.org_id).where(Membership.user_id.in_(user_ids)))
            )
            if org_ids:
                db.execute(delete(Organization).where(Organization.id.in_(org_ids)))
            db.execute(delete(User).where(User.id.in_(user_ids)))
            db.commit()
        finally:
            db.close()
