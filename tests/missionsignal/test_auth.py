"""Auth surface: signup form, login/logout, and the portal router.

The portal is a pure router now (no rendered page of its own): staff go to
Django admin, unverified accounts hit the activation paywall, verified users
without a project go to intake, first-time members get the snapshot tour, and
everyone else lands on their project dashboard. Rendered-content assertions
live with the pages that render (dashboard/snapshot tests).
"""
import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from openoutreach.core.models import Organization, OrganizationMember, Project


pytestmark = pytest.mark.django_db


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_user(username="pilot_user", password="testpass123"):
    return User.objects.create_user(username=username, password=password, email=f"{username}@example.com")


def _make_project(user, org_name="Test Org"):
    org = Organization.objects.create(name=org_name, website="https://example.org", mission="Help people.")
    project = Project.objects.create(organization=org, name="Main", programs="Programs here.")
    project.users.add(user)
    return project


SIGNUP = {
    "first_name": "New", "last_name": "User", "email": "newuser@example.org",
    "password1": "Str0ngPass!xyz", "password2": "Str0ngPass!xyz",
}


# ── Signup ────────────────────────────────────────────────────────────────────

def test_signup_creates_user(client):
    response = client.post(reverse("signup"), SIGNUP)
    assert User.objects.filter(email="newuser@example.org").exists()
    assert response.status_code == 302


def test_signup_redirects_to_portal(client):
    response = client.post(reverse("signup"), SIGNUP)
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


# ── Portal router ─────────────────────────────────────────────────────────────

def test_unauthenticated_portal_redirects_to_login(client):
    response = client.get(reverse("portal"))
    assert response.status_code == 302
    assert response["Location"].startswith("/accounts/login/")


def test_staff_routed_to_admin(client):
    user = _make_user("staffer")
    user.is_staff = True
    user.save()
    client.force_login(user)
    response = client.get(reverse("portal"))
    assert response.status_code == 302
    assert response["Location"] == "/admin/"


def test_unverified_user_without_project_hits_paywall(client):
    user = _make_user()
    client.force_login(user)
    response = client.get(reverse("portal"))
    assert response.status_code == 302
    assert response["Location"] == reverse("account-activate")


def test_first_time_member_routed_to_snapshot_tour(client):
    user = _make_user()
    project = _make_project(user)
    OrganizationMember.objects.create(user=user, project=project)  # has_toured=False
    client.force_login(user)
    response = client.get(reverse("portal"))
    assert response.status_code == 302
    assert response["Location"] == reverse("project-snapshot", kwargs={"pk": project.pk})


def test_toured_member_routed_to_own_dashboard(client):
    user = _make_user()
    project = _make_project(user)
    OrganizationMember.objects.create(user=user, project=project, has_toured=True)
    client.force_login(user)
    response = client.get(reverse("portal"))
    assert response.status_code == 302
    assert response["Location"] == reverse("project-dashboard", kwargs={"pk": project.pk})


def test_member_routed_to_own_project_not_another_orgs(client):
    user_a = _make_user("user_a", "testpass123")
    user_b = _make_user("user_b", "testpass123")
    project_a = _make_project(user_a, "Org A")
    project_b = _make_project(user_b, "Org B")

    client.force_login(user_a)
    response = client.get(reverse("portal"))
    assert response["Location"].endswith(f"/projects/{project_a.pk}/dashboard/")
    assert f"/projects/{project_b.pk}/" not in response["Location"]


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
