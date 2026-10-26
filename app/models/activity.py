"""Append-only activity feed; the substrate for the audit log in phase 7."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Uuid, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base
from .mixins import UUIDPrimaryKey


class Activity(UUIDPrimaryKey, Base):
    __tablename__ = "activity"
    __table_args__ = (
        Index("ix_activity_org_created", "org_id", "created_at"),
        Index("ix_activity_issue_created", "issue_id", "created_at"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE")
    )
    # Null for system-generated events (imports, webhooks, scheduled work).
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    issue_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("issues.id", ondelete="SET NULL")
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="SET NULL")
    )

    # e.g. "issue.created", "issue.status_changed", "comment.created"
    verb: Mapped[str] = mapped_column(String(48), nullable=False)
    payload: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
