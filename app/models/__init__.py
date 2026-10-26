"""Model registry. Importing this module registers every table on ``Base.metadata``."""

from __future__ import annotations

from .activity import Activity
from .issue import Comment, Issue, IssueLabel, IssuePriority, IssueStatus, Label
from .org import Membership, Organization, Role, User
from .project import Project

__all__ = [
    "Activity",
    "Comment",
    "Issue",
    "IssueLabel",
    "IssuePriority",
    "IssueStatus",
    "Label",
    "Membership",
    "Organization",
    "Project",
    "Role",
    "User",
]
