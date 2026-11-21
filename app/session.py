"""SQLite-backed implementation of Flask's SessionInterface."""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from flask import Flask, Request, Response
from flask.sessions import SessionInterface, SessionMixin
from sqlalchemy import update
from sqlalchemy.orm.exc import StaleDataError
from werkzeug.datastructures import CallbackDict

from .db import get_session
from .models import Session as SessionRow


class DatabaseSession(CallbackDict, SessionMixin):
    def __init__(self, initial: dict | None = None, sid: str | None = None) -> None:
        def on_update(self) -> None:
            self.modified = True

        super().__init__(initial, on_update)
        self.sid = sid
        self.modified = False
        self.accessed = False
        self.permanent = True


class DatabaseSessionInterface(SessionInterface):
    def __init__(
        self,
        cookie_name: str = "amoja_harbor_session",
        lifetime: timedelta = timedelta(days=14),
    ) -> None:
        self.cookie_name = cookie_name
        self.lifetime = lifetime

    def open_session(self, app: Flask, request: Request) -> DatabaseSession | None:
        sid = request.cookies.get(self.cookie_name)
        if not sid:
            # Not None: a null session cannot persist a CSRF token or flash message,
            # so start with an empty server-side session instead.
            return DatabaseSession()

        db = get_session()
        row = db.get(SessionRow, sid)
        now = datetime.now(UTC)
        if row is None or row.expires_at <= now:
            if row is not None:
                db.delete(row)
                db.commit()
            # Never return None: Flask turns that into a NullSession, which cannot
            # hold a CSRF token or a flash message.
            return DatabaseSession()

        # Touch the row with an immediate UPDATE rather than a pending ORM change.
        # If another request removes the row mid-flight (sign out everywhere, an
        # expired-session sweep), there is nothing left to flush against it.
        if now - row.last_seen_at >= timedelta(minutes=5):
            db.execute(update(SessionRow).where(SessionRow.id == sid).values(last_seen_at=now))
            db.commit()

        return DatabaseSession(dict(row.data), sid=sid)

    def save_session(self, app: Flask, session: DatabaseSession, response: Response) -> None:
        domain = self.get_cookie_domain(app)
        path = self.get_cookie_path(app)

        if not session:
            if session.modified:
                db = get_session()
                row = db.get(SessionRow, session.sid) if session.sid else None
                if row is not None:
                    db.delete(row)
                    try:
                        db.commit()
                    except StaleDataError:
                        # Another request already removed it; nothing to revoke.
                        db.rollback()
                response.delete_cookie(self.cookie_name, domain=domain, path=path)
            return

        db = get_session()
        now = datetime.now(UTC)
        expires_at = now + self.lifetime
        sid = session.sid or secrets.token_urlsafe(32)

        user_id: uuid.UUID | None = None
        raw_user_id = session.get("_user_id")
        if raw_user_id:
            try:
                user_id = uuid.UUID(raw_user_id)
            except ValueError:
                user_id = None

        row = db.get(SessionRow, sid, populate_existing=True)
        if row is None:
            row = SessionRow(
                id=sid,
                user_id=user_id,
                data=dict(session),
                expires_at=expires_at,
                last_seen_at=now,
            )
            db.add(row)
        else:
            row.user_id = user_id
            row.data = dict(session)
            row.expires_at = expires_at
            row.last_seen_at = now
        try:
            db.commit()
        except StaleDataError:
            # The row was revoked while the request was running (for example by
            # "sign out everywhere"); treat this device as signed out.
            db.rollback()
            response.delete_cookie(self.cookie_name, domain=domain, path=path)
            return

        response.set_cookie(
            self.cookie_name,
            sid,
            expires=expires_at,
            httponly=self.get_cookie_httponly(app),
            secure=self.get_cookie_secure(app),
            samesite=self.get_cookie_samesite(app),
            domain=domain,
            path=path,
        )

    @staticmethod
    def prune() -> int:
        """Delete expired sessions. Returns the number removed."""
        from sqlalchemy import delete

        db = get_session()
        result = db.execute(delete(SessionRow).where(SessionRow.expires_at <= datetime.now(UTC)))
        db.commit()
        return result.rowcount or 0
