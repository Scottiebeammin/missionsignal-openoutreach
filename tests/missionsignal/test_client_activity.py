"""ClientActivityTracker middleware + operator activity surfaces.

The middleware stamps OrganizationMember.last_seen_at / page_views for
authenticated non-staff hits on /projects/<pk>/ paths, throttled to one write
per 10-minute window (the throttle lives in the UPDATE's WHERE clause).
"""
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from openoutreach.core.models import Organization, OrganizationMember, Project

pytestmark = pytest.mark.django_db


@pytest.fixture
def member_setup(db):
    organization = Organization.objects.create(
        name="Bright Harbor Youth Alliance",
        website="https://brightharbor.example.org",
        mission="Youth development in Central Florida.",
    )
    project = Project.objects.create(
        organization=organization, name="Core Programs", programs="Mentoring.",
    )
    user = get_user_model().objects.create_user(username="activity-member", password="pw")
    project.users.add(user)
    member = OrganizationMember.objects.create(user=user, project=project)
    return project, user, member


def _project_url(project):
    return reverse("project-analysis-detail", kwargs={"pk": project.pk})


def test_first_project_hit_stamps_member(client, member_setup):
    project, user, member = member_setup
    client.force_login(user)

    response = client.get(_project_url(project))

    assert response.status_code == 200
    member.refresh_from_db()
    assert member.last_seen_at is not None
    assert member.page_views == 1


def test_hits_inside_throttle_window_count_once(client, member_setup):
    project, user, member = member_setup
    client.force_login(user)

    client.get(_project_url(project))
    client.get(_project_url(project))
    client.get(_project_url(project))

    member.refresh_from_db()
    assert member.page_views == 1
    first_seen = member.last_seen_at

    # A hit after the 10-minute window opens a new active window: +1 view, fresh stamp.
    OrganizationMember.objects.filter(pk=member.pk).update(
        last_seen_at=timezone.now() - timedelta(minutes=11),
    )
    client.get(_project_url(project))
    member.refresh_from_db()
    assert member.page_views == 2
    assert member.last_seen_at > first_seen - timedelta(minutes=11)


def test_staff_hits_are_not_tracked(client, member_setup):
    project, _user, _member = member_setup
    staff = get_user_model().objects.create_user(
        username="activity-staff", password="pw", is_staff=True,
    )
    staff_member = OrganizationMember.objects.create(user=staff, project=project)
    client.force_login(staff)

    response = client.get(_project_url(project))

    assert response.status_code == 200  # staff may view any project
    staff_member.refresh_from_db()
    assert staff_member.last_seen_at is None
    assert staff_member.page_views == 0


def test_non_project_paths_are_not_tracked(client, member_setup):
    _project, user, member = member_setup
    client.force_login(user)

    client.get("/resources/")

    member.refresh_from_db()
    assert member.last_seen_at is None
    assert member.page_views == 0


# --- operator surfaces -----------------------------------------------------------------


def test_operator_organizations_shows_last_seen_column(client, member_setup):
    project, _user, member = member_setup
    staff = get_user_model().objects.create_user(
        username="activity-operator", password="pw", is_staff=True,
    )
    client.force_login(staff)
    url = reverse("operator-organizations")

    # No activity yet — column renders "Never".
    response = client.get(url)
    assert response.status_code == 200
    content = response.content.decode()
    assert "Last Seen" in content
    assert "Never" in content

    # With activity — relative timestamp + summed page views.
    OrganizationMember.objects.filter(pk=member.pk).update(
        last_seen_at=timezone.now() - timedelta(hours=2), page_views=7,
    )
    response = client.get(url)
    content = response.content.decode()
    assert "ago" in content
    assert ">7</td>" in content
    row = next(p for p in response.context["projects"] if p.pk == project.pk)
    assert row.total_page_views == 7
    assert row.last_seen is not None


def test_operator_dashboard_active_this_week_stat(client, member_setup):
    _project, _user, member = member_setup
    staff = get_user_model().objects.create_user(
        username="activity-operator-dash", password="pw", is_staff=True,
    )
    client.force_login(staff)
    url = reverse("operator-dashboard")

    response = client.get(url)
    assert response.context["active_orgs_week"] == 0

    OrganizationMember.objects.filter(pk=member.pk).update(last_seen_at=timezone.now())
    response = client.get(url)
    assert response.context["active_orgs_week"] == 1
    assert "Active this week" in response.content.decode()
