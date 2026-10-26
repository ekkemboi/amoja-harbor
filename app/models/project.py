"""Projects: the container every issue belongs to."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base
from .mixins import Timestamps, UUIDPrimaryKey


class Project(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "projects"
    __table_args__ = (UniqueConstraint("org_id", "key", name="uq_projects_org_key"),)

    org_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    # Short human key used in issue identifiers, e.g. "HRB-142".
    key: Mapped[str] = mapped_column(String(8))
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)

    # Allocated with UPDATE ... RETURNING so concurrent issue creation cannot collide.
    issue_counter: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )

    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
