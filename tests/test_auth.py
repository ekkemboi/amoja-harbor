from __future__ import annotations

from app.models import Membership, Role, Session, User
from sqlalchemy import delete, func, select

from tests.factories import PASSWORD, signin


def signup(client, factory, *, email=None, org_name="Analytical Engine"):
    email = email or factory.email()
    response = client.post(
        "/signup",
        data={
            "name": "Ada Lovelace",
            "email": email,
            "password": PASSWORD,
            "org_name": org_name,
        },
    )
    return response, email


def test_signup_creates_workspace_and_owner_membership(client, factory, app):
    response, email = signup(client, factory)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")

    page = client.get(response.headers["Location"])
    assert page.status_code == 200
    assert b"Analytical Engine" in page.data
    assert b"owner" in page.data

    with app.extensions["session_factory"]() as db:
        user = db.scalar(select(User).where(User.email == email))
        membership = db.scalar(select(Membership).where(Membership.user_id == user.id))
        assert membership.role is Role.OWNER


def test_signup_rejects_a_duplicate_email(client, factory):
    _, email = signup(client, factory)

    # A fresh client: the first signup left the session authenticated, and
    # /signup redirects signed-in users.
    anonymous = client.application.test_client()
    response = anonymous.post(
        "/signup",
        data={
            "name": "Ada Lovelace",
            "email": email,
            "password": PASSWORD,
            "org_name": "Second Workspace",
        },
    )

    assert response.status_code == 400
    assert b"already registered" in response.data


def test_signup_rejects_a_short_password(client, factory):
    response = client.post(
        "/signup",
        data={
            "name": "Ada Lovelace",
            "email": factory.email(),
            "password": "short",
            "org_name": "Analytical Engine",
        },
    )

    assert response.status_code == 400
    assert b"at least 10 characters" in response.data


def test_signin_rejects_a_bad_password(client, factory):
    user = factory.user()

    response = signin(client, user.email, "not-the-password")

    assert response.status_code == 401
    assert b"incorrect" in response.data


def test_signin_then_signout_revokes_the_session(client, factory, app):
    user = factory.user()

    assert signin(client, user.email).status_code == 302

    with app.extensions["session_factory"]() as db:
        session_count = db.scalar(
            select(func.count()).select_from(Session).where(Session.user_id == user.id)
        )
    assert session_count == 1

    assert client.post("/signout").status_code == 302

    with app.extensions["session_factory"]() as db:
        session_count = db.scalar(
            select(func.count()).select_from(Session).where(Session.user_id == user.id)
        )
    assert session_count == 0

    assert client.get("/app").status_code == 302


def test_anonymous_visit_to_a_workspace_redirects_to_signin(client, factory):
    owner = factory.user()
    org = factory.org(owner=owner)

    response = client.get(f"/app/{org.slug}/")

    assert response.status_code == 302
    assert "/signin" in response.headers["Location"]


def test_signin_ignores_an_offsite_next_parameter(client, factory):
    user = factory.user()

    response = client.post(
        "/signin?next=https://evil.example/steal",
        data={"email": user.email, "password": PASSWORD},
    )

    assert response.status_code == 302
    assert "evil.example" not in response.headers["Location"]


def test_next_parameter_is_honoured_for_local_paths(client, factory):
    user = factory.user()

    response = client.post(
        "/signin?next=/app",
        data={"email": user.email, "password": PASSWORD},
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/app"


def test_stale_session_cookie_is_signed_out_cleanly(client, factory, app):
    """A cookie whose server-side row vanished must not produce a 500."""
    user = factory.user()
    assert signin(client, user.email).status_code == 302

    with app.extensions["session_factory"]() as db:
        db.execute(delete(Session))
        db.commit()

    response = client.get("/app")

    assert response.status_code == 302
    assert "/signin" in response.headers["Location"]

    page = client.get(response.headers["Location"])
    assert page.status_code == 200
    assert b"Sign in" in page.data
