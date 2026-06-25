import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from openoutreach.core.models import Organization, OrganizationMember, Project
from openoutreach.signals.models import PilotProfile


pytestmark = pytest.mark.django_db


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_user(username="pilot_user", password="testpass123"):
    return User.objects.create_user(username=username, password=password, email=f"{username}@example.com")


def _make_project(user, org_name="Test Org"):
    org = Organization.objects.create(name=org_name, website="https://example.org", mission="Help people.")
    project = Project.objects.create(organization=org, name="Main", programs="Programs here.")
    project.users.add(user)
    return project


# ── Signup ────────────────────────────────────────────────────────────────────

def test_signup_creates_user(client):
    response = client.post(reverse("signup"), {
        "username": "newuser",
        "password1": "Str0ngPass!xyz",
        "password2": "Str0ngPass!xyz",
    })
    assert User.objects.filter(username="newuser").exists()
    assert response.status_code == 302


def test_signup_redirects_to_portal(client):
    response = client.post(reverse("signup"), {
        "username": "newuser2",
        "password1": "Str0ngPass!xyz",
        "password2": "Str0ngPass!xyz",
    })
    assert response["Location"] == "/portal/"


def test_signup_page_renders(client):
    response = client.get(reverse("signup"))
    assert response.status_code == 200


# ── Login / logout ────────────────────────────────────────────────────────────

def test_login_redirects_to_portal(client):
    _make_user("logintest", "testpass123")
    response = client.post(reverse("login"), {"username": "logintest", "password": "testpass123"})
    assert response.status_code == 302
    assert response["Location"] == "/portal/"


def test_logout_clears_session(client):
    user = _make_user("logouttest", "testpass123")
    client.force_login(user)
    client.post(reverse("logout"))
    response = client.get(reverse("portal"))
    assert response.status_code == 302
    assert "/accounts/login/" in response["Location"]


# ── Portal access ─────────────────────────────────────────────────────────────

def test_unauthenticated_portal_redirects_to_login(client):
    response = client.get(reverse("portal"))
    assert response.status_code == 302
    assert response["Location"].startswith("/accounts/login/")


def test_portal_renders_for_authenticated_user(client):
    user = _make_user()
    client.force_login(user)
    response = client.get(reverse("portal"))
    assert response.status_code == 200


def test_portal_shows_empty_state_when_no_project(client):
    user = _make_user()
    client.force_login(user)
    response = client.get(reverse("portal"))
    assert b"being set up" in response.content


def test_portal_shows_org_name_when_project_linked(client):
    user = _make_user()
    _make_project(user, "Empowered Girls Inc")
    client.force_login(user)
    response = client.get(reverse("portal"))
    assert b"Empowered Girls Inc" in response.content


# ── Data isolation ────────────────────────────────────────────────────────────

def test_user_cannot_see_another_orgs_portal(client):
    user_a = _make_user("user_a", "testpass123")
    user_b = _make_user("user_b", "testpass123")
    _make_project(user_a, "Org A")
    _make_project(user_b, "Org B")

    client.force_login(user_a)
    response = client.get(reverse("portal"))
    assert b"Org A" in response.content
    assert b"Org B" not in response.content


# ── Pilot status ──────────────────────────────────────────────────────────────

def test_portal_shows_pilot_status(client):
    user = _make_user()
    project = _make_project(user)
    PilotProfile.objects.create(
        project=project,
        organization_name=project.organization.name,
        lifecycle_status=PilotProfile.LifecycleStatus.SNAPSHOT_IN_PROGRESS,
        snapshot_status=PilotProfile.SnapshotStatus.BUILDING_SNAPSHOT,
    )
    client.force_login(user)
    response = client.get(reverse("portal"))
    assert response.status_code == 200
    assert b"being built" in response.content


def test_portal_shows_snapshot_link_when_delivered(client):
    user = _make_user()
    project = _make_project(user)
    PilotProfile.objects.create(
        project=project,
        organization_name=project.organization.name,
        lifecycle_status=PilotProfile.LifecycleStatus.SNAPSHOT_DELIVERED,
        snapshot_status=PilotProfile.SnapshotStatus.DELIVERED,
    )
    client.force_login(user)
    response = client.get(reverse("portal"))
    assert b"View Snapshot" in response.content or b"Open Snapshot" in response.content


def test_portal_shows_placeholder_when_snapshot_not_delivered(client):
    user = _make_user()
    project = _make_project(user)
    PilotProfile.objects.create(
        project=project,
        organization_name=project.organization.name,
        lifecycle_status=PilotProfile.LifecycleStatus.SNAPSHOT_IN_PROGRESS,
        snapshot_status=PilotProfile.SnapshotStatus.BUILDING_SNAPSHOT,
    )
    client.force_login(user)
    response = client.get(reverse("portal"))
    assert b"Available after delivery" in response.content


# ── OrganizationMember ────────────────────────────────────────────────────────

def test_organization_member_creation(db):
    user = _make_user()
    project = _make_project(user)
    member = OrganizationMember.objects.create(
        user=user,
        project=project,
        role=OrganizationMember.Role.EXECUTIVE_DIRECTOR,
    )
    assert member.role == "executive_director"
    assert str(member) == f"{user} — {project} (executive_director)"


def test_organization_member_unique_constraint(db):
    from django.db import IntegrityError
    user = _make_user()
    project = _make_project(user)
    OrganizationMember.objects.create(user=user, project=project)
    with pytest.raises(IntegrityError):
        OrganizationMember.objects.create(user=user, project=project)
