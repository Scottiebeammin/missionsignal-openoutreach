import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from openoutreach.core.models import Organization, Project
from openoutreach.signals.analysis_service import analyze_project


@pytest.fixture
def analyzed_project(db):
    user = get_user_model().objects.create_user(
        username="funding-dashboard-member",
        password="password",
    )
    organization = Organization.objects.create(
        name="BridgeForward Digital Futures",
        website="https://bridgeforward.example",
        mission="Help youth build careers and improve economic mobility.",
        city="Detroit",
        county="Wayne",
        state="Michigan",
        service_area_notes="Serves neighborhoods across Wayne County.",
        outcomes_and_impact=["85% credential completion", "120 graduates placed"],
        budget_range="$250K - $1M",
        current_funding_sources=["Community Foundation", "City workforce grant"],
        existing_partnerships=["Local College", "Employer Council"],
    )
    project = Project.objects.create(
        organization=organization,
        name="Primary Initiative",
        programs=(
            "Career readiness, digital skills training, mentoring, and small "
            "business coaching for youth."
        ),
    )
    project.users.add(user)
    analyze_project(project)
    return project, user


def test_project_member_can_view_real_funding_dashboard(client, analyzed_project):
    project, user = analyzed_project
    client.force_login(user)

    response = client.get(reverse("project-funding", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Funding Dashboard" in content
    assert "Funding V2" in content
    assert "Funding Readiness Score" in content
    assert "Funding Themes" in content
    assert "Recommended Funder Types" in content
    assert "Local Government Opportunity Snapshot" in content
    assert "Grant Readiness Checklist" in content
    assert "Recommended Funding Actions" in content
    assert reverse("project-government", kwargs={"pk": project.pk}) in content
    assert "Discovery is not enabled yet." not in content


def test_funding_dashboard_renders_deterministic_themes(client, analyzed_project):
    project, user = analyzed_project
    client.force_login(user)

    response = client.get(reverse("project-funding", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert "Workforce Development" in content
    assert "Digital Equity" in content
    assert "Youth Development" in content
    assert "Career Readiness" in content
    assert "Community Development" in content


def test_funding_dashboard_shows_all_required_funder_types(client, analyzed_project):
    project, user = analyzed_project
    client.force_login(user)

    response = client.get(reverse("project-funding", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert "Community Foundations" in content
    assert "Corporate Foundations" in content
    assert "Local Government" in content
    assert "State Government" in content
    assert "Federal Government" in content
    assert "Workforce Development Boards" in content
    assert "United Way Organizations" in content
    assert "Family Foundations" in content


def test_funding_dashboard_explains_local_government_lane(client, analyzed_project):
    project, user = analyzed_project
    client.force_login(user)

    response = client.get(reverse("project-funding", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert "Local Government Opportunity Snapshot" in content
    assert "Local Government" in content
    assert "City grants" in content
    assert "County grants" in content
    assert "youth services funding" in content
    assert "workforce programs" in content
    assert "economic development programs" in content
    assert "digital equity initiatives" in content
    assert "community development programs" in content
    assert "Public-sector service contracts" in content
    assert "RFPs" in content


def test_funding_dashboard_checklist_shows_complete_and_missing_items(client, db):
    user = get_user_model().objects.create_user(
        username="funding-dashboard-gaps",
        password="password",
    )
    organization = Organization.objects.create(
        name="Gap Works",
        website="https://gap-works.example",
        mission="Help youth prepare for careers.",
        city="Detroit",
        state="Michigan",
    )
    project = Project.objects.create(
        organization=organization,
        name="Primary Initiative",
        programs="Career readiness programming for youth.",
    )
    project.users.add(user)
    analyze_project(project)
    client.force_login(user)

    response = client.get(reverse("project-funding", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert "Complete" in content
    assert "Missing" in content
    assert "Mission Statement" in content
    assert "Programs Defined" in content
    assert "Organization Type" in content
    assert "Service Geography" in content
    assert "Target Population" in content
    assert "Outcomes / Impact" in content
    assert "Budget Range" in content
    assert "Current Funding Sources" in content
    assert "Existing Partnerships" in content
    assert "Confirm the organization type" in content
    assert "Collect two or three outcome metrics" in content
    assert "Prepare a simple program budget range" in content


def test_funding_dashboard_recommended_actions_are_gap_specific(client, analyzed_project):
    project, user = analyzed_project
    client.force_login(user)

    response = client.get(reverse("project-funding", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert "Use the Local Government snapshot to shortlist city, county, workforce, economic development, and digital equity lanes before broad grant search." in content
    assert "Turn Primary Initiative into a one-page funding brief with themes, geography, outcomes, budget, and partner evidence." in content
    assert "Review and approve the generated funding themes." not in content


def test_non_member_cannot_view_funding_dashboard(client, analyzed_project):
    project, _ = analyzed_project
    outsider = get_user_model().objects.create_user(
        username="funding-dashboard-nonmember",
        password="password",
    )
    client.force_login(outsider)

    response = client.get(reverse("project-funding", kwargs={"pk": project.pk}))

    assert response.status_code == 404


def test_government_dashboard_link_from_funding_route_works(client, analyzed_project):
    project, user = analyzed_project
    client.force_login(user)

    member_response = client.get(reverse("project-government", kwargs={"pk": project.pk}))
    member_content = member_response.content.decode()

    assert member_response.status_code == 200
    assert "Government Dashboard" in member_content
    assert "Government Opportunity Readiness Score" in member_content
