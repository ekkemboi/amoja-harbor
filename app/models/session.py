"""Server-side sessions.

Flask's default session is a signed cookie: it cannot be revoked and it leaks every
key you put in it. Amoja Harbor stores session data in SQLite instead, so "sign out
everywhere" is a DELETE and a stolen cookie can be killed server-side.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, ForeignKey, String, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base
from .types import UTCDateTime


class Session(Base):
    __tablename__ = "sessions"

    # The opaque cookie value, never a user-facing identifier.
    id: Mapped[str] = mapped_column(String(64), primary_key=True)

    # Null between "cookie issued" and "user signed in" (flash messages, CSRF).
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    data: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict, server_default=text("'{}'")
    )
    user_agent: Mapped[str | None] = mapped_column(String(255))
    ip_address: Mapped[str | None] = mapped_column(String(45))

    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        UTCDateTime, nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, index=True)
