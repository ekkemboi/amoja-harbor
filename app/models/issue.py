"""Issues, comments, labels, and the join between issues and labels."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base
from .mixins import Timestamps, UUIDPrimaryKey
from .org import User


class IssueStatus(StrEnum):
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    CANCELED = "canceled"


class IssuePriority(StrEnum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


def _enum_column(enum: type[StrEnum], name: str, length: int) -> Enum:
    return Enum(
        enum,
        name=name,
        native_enum=False,
        length=length,
        create_constraint=True,
        values_callable=lambda members: [member.value for member in members],
        validate_strings=True,
    )


class Issue(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "issues"
    __table_args__ = (
        UniqueConstraint("project_id", "number", name="uq_issues_project_number"),
        Index("ix_issues_project_status", "project_id", "status"),
        Index("ix_issues_org_status_updated", "org_id", "status", "updated_at"),
        Index("ix_issues_assignee", "assignee_id"),
    )

    # Denormalized org_id so every authorization check is a single-column filter and
    # never requires a join through projects.
    org_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE")
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE")
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False)

    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[IssueStatus] = mapped_column(
        _enum_column(IssueStatus, "issue_status", 16),
        nullable=False,
        default=IssueStatus.TODO,
        server_default=IssueStatus.TODO.value,
    )
    priority: Mapped[IssuePriority] = mapped_column(
        _enum_column(IssuePriority, "issue_priority", 12),
        nullable=False,
        default=IssuePriority.NONE,
        server_default=IssuePriority.NONE.value,
    )

    assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )
    due_date: Mapped[date | None] = mapped_column(Date)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    assignee: Mapped[User | None] = relationship(foreign_keys=[assignee_id])
    created_by: Mapped[User] = relationship(foreign_keys=[created_by_id])
    comments: Mapped[list[Comment]] = relationship(
        back_populates="issue", cascade="all, delete-orphan", order_by="Comment.created_at"
    )
    labels: Mapped[list[Label]] = relationship(secondary="issue_labels", back_populates="issues")


class Comment(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "comments"
    __table_args__ = (Index("ix_comments_issue_created", "issue_id", "created_at"),)

    org_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    issue_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("issues.id", ondelete="CASCADE"))
    author_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )

    body: Mapped[str] = mapped_column(Text)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    issue: Mapped[Issue] = relationship(back_populates="comments")
    author: Mapped[User] = relationship()


class Label(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "labels"
    __table_args__ = (UniqueConstraint("org_id", "name", name="uq_labels_org_name"),)

    org_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(32))
    # Hex color used for the label chip.
    color: Mapped[str] = mapped_column(String(7), default="#64748b", server_default="#64748b")

    issues: Mapped[list[Issue]] = relationship(secondary="issue_labels", back_populates="labels")


class IssueLabel(Base):
    __tablename__ = "issue_labels"

    issue_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("issues.id", ondelete="CASCADE"), primary_key=True
    )
    label_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("labels.id", ondelete="CASCADE"), primary_key=True, index=True
    )
