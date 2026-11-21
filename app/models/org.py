"""Organizations, users, and the membership that joins them."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    Enum,
    ForeignKey,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base
from .mixins import Timestamps, UUIDPrimaryKey
from .types import UTCDateTime


class Role(StrEnum):
    """Ordered from most to least privileged; see ``Role.allows``."""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"

    @property
    def rank(self) -> int:
        return _ROLE_RANK[self]

    def allows(self, required: Role) -> bool:
        return self.rank >= required.rank


_ROLE_RANK = {Role.OWNER: 4, Role.ADMIN: 3, Role.MEMBER: 2, Role.VIEWER: 1}


def _role_column() -> Enum:
    # native_enum=False keeps roles as VARCHAR + CHECK, so adding a role later is a
    # plain constraint swap instead of an ALTER TYPE dance.
    return Enum(
        Role,
        name="membership_role",
        native_enum=False,
        length=16,
        create_constraint=True,
        values_callable=lambda enum: [member.value for member in enum],
        validate_strings=True,
    )


class Organization(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "organizations"

    slug: Mapped[str] = mapped_column(String(48), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))

    memberships: Mapped[list[Membership]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )


class User(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "users"
    __table_args__ = (
        # Emails are stored already normalized, so a plain unique index is enough and
        # this constraint catches any code path that forgets to lowercase.
        CheckConstraint("email = lower(email)", name="ck_users_email_lowercase"),
    )

    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    email_verified_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    last_seen_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    # Flask-Login's protocol. Accounts are not deactivated in Amoja Harbor yet, so
    # is_active is always True.
    @property
    def is_active(self) -> bool:
        return True

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_anonymous(self) -> bool:
        return False

    def get_id(self) -> str:
        return str(self.id)


class Membership(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("org_id", "user_id", name="uq_memberships_org_user"),)

    org_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[Role] = mapped_column(
        _role_column(), nullable=False, default=Role.MEMBER, server_default=Role.MEMBER.value
    )

    organization: Mapped[Organization] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship()
