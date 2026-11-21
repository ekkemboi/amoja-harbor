"""Schema-level guarantees: the database, not just the ORM, enforces the rules."""

from __future__ import annotations

from sqlalchemy import inspect, text

EXPECTED_TABLES = {
    "activity",
    "comments",
    "issue_labels",
    "issues",
    "labels",
    "memberships",
    "organizations",
    "projects",
    "users",
}

# Enum guards are VARCHAR + CHECK (native_enum=False), so they show up here.
EXPECTED_CHECK_CONSTRAINTS = {
    "ck_users_email_lowercase",
    "issue_priority",
    "issue_status",
    "membership_role",
}


def test_every_model_table_exists(app):
    present = set(inspect(app.extensions["engine"]).get_table_names())

    assert present >= EXPECTED_TABLES


def test_enum_email_and_foreign_key_guards_are_enforced_in_sqlite(app):
    with app.extensions["engine"].connect() as connection:
        schema = "\n".join(
            sql
            for sql in connection.execute(
                text("select sql from sqlite_master where type = 'table'")
            ).scalars()
            if sql
        )
        foreign_keys = connection.execute(text("pragma foreign_keys")).scalar()

    assert foreign_keys == 1
    assert all(name in schema for name in EXPECTED_CHECK_CONSTRAINTS)
