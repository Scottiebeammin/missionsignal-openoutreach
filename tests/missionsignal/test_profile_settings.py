"""Client profile settings: areas-of-support editor, seat authority, website check.

- Areas of support drive matching, so edits are gated to the account admin
  (first seat). Removals persist as exclusions the analyzer must never
  re-infer from mission/website text.
- Invite acceptance creates a member row; the first seat on a project becomes
  the account admin, later seats join as regular members.
- The website scan compares profile claims (programs + areas) against the live
  site text and points out anything not visible.
"""
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from openoutreach.core.access import user_is_project_admin
from openoutreach.core.models import OrganizationMember
from openoutreach.funding.models import FundingCriteria
from openoutreach.signals.demo import seed_missionsignal_demo
from openoutreach.signals.invites import make_invite_token

pytestmark = pytest.mark.django_db


@pytest.fixture
def workspace(db):
    user, organization, project = seed_missionsignal_demo()
    OrganizationMember.objects.update_or_create(
        user=user, project=project, defaults={"is_admin": True},
    )
    return user, organization, project


@pytest.fixture
def second_seat(workspace):
    _user, _organization, project = workspace
    other = get_user_model().objects.create_user(username="seat2", password="x")
    project.users.add(other)
    OrganizationMember.objects.create(user=other, project=project)
    return other


def _focus_post(client, project, action, value):
    return client.post(
        reverse("project-focus-areas", kwargs={"pk": project.pk}),
        {"action": action, "value": value},
    )


# ── Seat authority ────────────────────────────────────────────────────────────

def test_first_invite_seat_becomes_admin_second_does_not(db):
    from openoutreach.core.models import Organization, Project
    org = Organization.objects.create(name="Two Seat Org", mission="Serve.")
    project = Project.objects.create(name="Two Seat Org", organization=org)
    url = f"/invite/{make_invite_token(project.pk)}/"

    from django.test import Client
    for email in ("first@twoseat.org", "second@twoseat.org"):
        Client().post(url, {
            "first_name": email.split("@")[0].title(),
            "email": email,
            "password1": "web-of-opportunity-9", "password2": "web-of-opportunity-9",
        }, HTTP_HOST="localhost")

    members = {m.user.email: m for m in OrganizationMember.objects.filter(project=project)}
    assert members["first@twoseat.org"].is_admin is True
    assert members["second@twoseat.org"].is_admin is False
    assert user_is_project_admin(members["first@twoseat.org"].user, project)
    assert not user_is_project_admin(members["second@twoseat.org"].user, project)


def test_non_admin_seat_cannot_edit_focus_areas(client, workspace, second_seat):
    _user, organization, project = workspace
    before = list(organization.focus_areas)
    client.force_login(second_seat)
    response = _focus_post(client, project, "add", "Housing")
    assert response.status_code == 403
    organization.refresh_from_db()
    assert organization.focus_areas == before


# ── Areas-of-support editor ───────────────────────────────────────────────────

def test_admin_adds_area_and_matching_criteria_refresh(client, workspace):
    user, organization, project = workspace
    client.force_login(user)
    response = _focus_post(client, project, "add", "housing")  # canonicalized
    assert response.status_code == 302
    organization.refresh_from_db()
    assert "Housing" in organization.focus_areas
    criteria = FundingCriteria.objects.get(project=project)
    assert "Housing" in criteria.focus_areas  # analysis re-ran immediately


def test_removed_area_stays_removed_after_reanalysis(client, workspace):
    user, organization, project = workspace
    client.force_login(user)
    # "Workforce Development" is inferable from the demo mission/programs text,
    # so without the exclusion the next analysis would resurrect it.
    assert "Workforce Development" in organization.focus_areas
    response = _focus_post(client, project, "remove", "Workforce Development")
    assert response.status_code == 302
    organization.refresh_from_db()
    assert "Workforce Development" not in organization.focus_areas
    assert "Workforce Development" in organization.excluded_focus_areas

    from openoutreach.signals.analysis_service import analyze_project
    analyze_project(project, mode="deterministic")
    organization.refresh_from_db()
    assert "Workforce Development" not in organization.focus_areas


def test_re_adding_lifts_the_exclusion(client, workspace):
    user, organization, project = workspace
    client.force_login(user)
    _focus_post(client, project, "remove", "Education")
    _focus_post(client, project, "add", "Education")
    organization.refresh_from_db()
    assert "Education" in organization.focus_areas
    assert "Education" not in organization.excluded_focus_areas


def test_settings_page_shows_editor_to_admin_and_note_to_member(client, workspace, second_seat):
    user, _organization, project = workspace
    url = reverse("project-analysis-detail", kwargs={"pk": project.pk})

    client.force_login(user)
    admin_page = client.get(url).content.decode()
    assert "Areas of Support" in admin_page
    assert "Add area" in admin_page

    client.force_login(second_seat)
    member_page = client.get(url).content.decode()
    assert "Only your account admin can change areas of support." in member_page
    assert "Add area" not in member_page


def test_organization_page_lists_seats_with_admin_badge(client, workspace, second_seat):
    user, _organization, project = workspace
    client.force_login(user)
    page = client.get(reverse("project-organization", kwargs={"pk": project.pk})).content.decode()
    assert "Team &amp; Seats" in page
    assert "Admin" in page
    assert "seat2" in page


# ── Website check ─────────────────────────────────────────────────────────────

def test_website_scan_points_out_missing_programs(client, workspace):
    user, organization, project = workspace
    project.program_summaries = [
        {"name": "Digital Skills Lab", "description": "x"},
        {"name": "Career Mentorship Circle", "description": "x"},
    ]
    project.save(update_fields=["program_summaries"])
    organization.focus_areas = ["Youth Development"]
    organization.save(update_fields=["focus_areas"])

    site_text = "We run the Digital Skills Lab for youth development across Orlando."
    client.force_login(user)
    with patch("openoutreach.signals.website_verification.scrape_website_text", return_value=site_text):
        response = client.post(reverse("project-website-scan", kwargs={"pk": project.pk}))
    assert response.status_code == 302

    organization.refresh_from_db()
    report = organization.website_check
    assert report["status"] == "ok"
    found = {item["claim"] for item in report["found"]}
    missing = {item["claim"] for item in report["missing"]}
    assert "Digital Skills Lab" in found
    assert "Youth Development" in found
    assert "Career Mentorship Circle" in missing

    page = client.get(reverse("project-analysis-detail", kwargs={"pk": project.pk})).content.decode()
    assert "Not visible on your website" in page
    assert "Career Mentorship Circle" in page


def test_website_scan_handles_unreachable_and_missing_site(client, workspace):
    user, organization, project = workspace
    client.force_login(user)
    with patch("openoutreach.signals.website_verification.scrape_website_text", return_value=""):
        client.post(reverse("project-website-scan", kwargs={"pk": project.pk}))
    organization.refresh_from_db()
    assert organization.website_check["status"] == "unreachable"

    organization.website = ""
    organization.save(update_fields=["website"])
    client.post(reverse("project-website-scan", kwargs={"pk": project.pk}))
    organization.refresh_from_db()
    assert organization.website_check["status"] == "no_website"
