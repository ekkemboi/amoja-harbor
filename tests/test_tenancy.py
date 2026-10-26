from __future__ import annotations

import pytest
from app.models import Membership, Role
from sqlalchemy import select

from tests.factories import signin


@pytest.mark.parametrize(
    ("actor", "required", "allowed"),
    [
        (Role.OWNER, Role.OWNER, True),
        (Role.OWNER, Role.VIEWER, True),
        (Role.ADMIN, Role.ADMIN, True),
        (Role.ADMIN, Role.OWNER, False),
        (Role.MEMBER, Role.MEMBER, True),
        (Role.MEMBER, Role.ADMIN, False),
        (Role.VIEWER, Role.MEMBER, False),
        (Role.VIEWER, Role.VIEWER, True),
    ],
)
def test_role_matrix(actor, required, allowed):
    assert actor.allows(required) is allowed


def test_non_member_sees_404_not_403(client, factory):
    owner = factory.user()
    org = factory.org(owner=owner)
    outsider = factory.user()

    signin(client, outsider.email)
    response = client.get(f"/app/{org.slug}/")

    # 404 avoids confirming that someone else's workspace exists.
    assert response.status_code == 404


def test_viewer_cannot_change_roles(client, factory):
    owner = factory.user()
    org = factory.org(owner=owner)
    viewer = factory.user()
    factory.member(org, viewer, Role.VIEWER)
    target = factory.user()
    target_membership = factory.member(org, target, Role.VIEWER)

    signin(client, viewer.email)
    response = client.post(
        f"/app/{org.slug}/members/{target_membership.id}/role",
        data={"role": "admin"},
    )

    assert response.status_code == 403


def test_member_cannot_change_roles(client, factory):
    owner = factory.user()
    org = factory.org(owner=owner)
    member = factory.user()
    factory.member(org, member, Role.MEMBER)
    target = factory.user()
    target_membership = factory.member(org, target, Role.MEMBER)

    signin(client, member.email)
    response = client.post(
        f"/app/{org.slug}/members/{target_membership.id}/role",
        data={"role": "admin"},
    )

    assert response.status_code == 403


def test_admin_can_change_a_member_role(client, factory, app):
    owner = factory.user()
    org = factory.org(owner=owner)
    admin = factory.user()
    factory.member(org, admin, Role.ADMIN)
    target = factory.user()
    target_membership = factory.member(org, target, Role.MEMBER)

    signin(client, admin.email)
    response = client.post(
        f"/app/{org.slug}/members/{target_membership.id}/role",
        data={"role": "viewer"},
    )

    assert response.status_code == 302

    with app.extensions["session_factory"]() as db:
        role = db.scalar(select(Membership.role).where(Membership.id == target_membership.id))
    assert role is Role.VIEWER


def test_admin_cannot_grant_a_role_above_their_own(client, factory):
    owner = factory.user()
    org = factory.org(owner=owner)
    admin = factory.user()
    factory.member(org, admin, Role.ADMIN)
    target = factory.user()
    target_membership = factory.member(org, target, Role.MEMBER)

    signin(client, admin.email)
    response = client.post(
        f"/app/{org.slug}/members/{target_membership.id}/role",
        data={"role": "owner"},
    )

    assert response.status_code == 403


def test_cannot_change_your_own_role(client, factory, app):
    owner = factory.user()
    org = factory.org(owner=owner)
    admin = factory.user()
    admin_membership = factory.member(org, admin, Role.ADMIN)

    signin(client, admin.email)
    response = client.post(
        f"/app/{org.slug}/members/{admin_membership.id}/role",
        data={"role": "owner"},
    )

    assert response.status_code == 400


def test_unknown_role_is_rejected(client, factory):
    owner = factory.user()
    org = factory.org(owner=owner)
    target = factory.user()
    target_membership = factory.member(org, target, Role.MEMBER)

    signin(client, owner.email)
    response = client.post(
        f"/app/{org.slug}/members/{target_membership.id}/role",
        data={"role": "superuser"},
    )

    assert response.status_code == 400


def test_admin_cannot_touch_another_orgs_membership(client, factory):
    owner_a = factory.user()
    org_a = factory.org(owner=owner_a)
    admin_a = factory.user()
    factory.member(org_a, admin_a, Role.ADMIN)

    owner_b = factory.user()
    org_b = factory.org(owner=owner_b)
    target_b = factory.user()
    membership_b = factory.member(org_b, target_b, Role.MEMBER)

    signin(client, admin_a.email)
    response = client.post(
        f"/app/{org_a.slug}/members/{membership_b.id}/role",
        data={"role": "viewer"},
    )

    assert response.status_code == 404


def test_admin_can_remove_a_member(client, factory, app):
    owner = factory.user()
    org = factory.org(owner=owner)
    admin = factory.user()
    factory.member(org, admin, Role.ADMIN)
    target = factory.user()
    target_membership = factory.member(org, target, Role.MEMBER)

    signin(client, admin.email)
    response = client.post(f"/app/{org.slug}/members/{target_membership.id}/remove")

    assert response.status_code == 302
    with app.extensions["session_factory"]() as db:
        assert db.get(Membership, target_membership.id) is None
