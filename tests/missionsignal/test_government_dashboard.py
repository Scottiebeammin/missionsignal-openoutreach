import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from openoutreach.core.models import Organization, Project
from openoutreach.signals.analysis_service import analyze_project


@pytest.fixture
def government_project(db):
    user = get_user_model().objects.create_user(
        username="government-dashboard-member",
        password="password",
    )
    organization = Organization.objects.create(
        name="Civic Futures",
        website="https://civic-futures.example",
        mission="Help youth build careers through digital skills and mentoring.",
        organization_type="Nonprofit",
        city="Detroit",
        county="Wayne",
        state="Michigan",
        service_area_notes="Serves neighborhoods across Wayne County.",
        outcomes_and_impact=["85% credential completion", "120 graduates placed"],
        budget_range="$250K - $1M",
        current_funding_sources=["City workforce grant"],
        existing_partnerships=["Public Library", "Workforce Board"],
    )
    project = Project.objects.create(
        organization=organization,
        name="Primary Initiative",
        programs="Career readiness, digital skills training, mentoring, and job placement.",
    )
    project.users.add(user)
    analyze_project(project)
    return project, user


def test_project_member_can_view_government_dashboard(client, government_project):
    project, user = government_project
    client.force_login(user)

    response = client.get(reverse("project-government", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Government Dashboard" in content
    assert "Government Opportunity Readiness Score" in content
    assert "Relevant Public-Sector Lanes" in content
    assert "Recommended Government Entity Types" in content
    assert "Government Engagement Checklist" in content
    assert "Recommended Government Actions" in content
    assert reverse("project-mission-brief", kwargs={"pk": project.pk}) in content
    assert reverse("project-funding", kwargs={"pk": project.pk}) in content
    assert "placeholder" not in content.casefold()


def test_non_member_cannot_view_government_dashboard(client, government_project):
    project, _ = government_project
    outsider = get_user_model().objects.create_user(
        username="government-dashboard-outsider",
        password="password",
    )
    client.force_login(outsider)

    response = client.get(reverse("project-government", kwargs={"pk": project.pk}))

    assert response.status_code == 404


def test_government_dashboard_public_sector_lanes_render(client, government_project):
    project, user = government_project
    client.force_login(user)

    response = client.get(reverse("project-government", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert "City Grants" in content
    assert "County Grants" in content
    assert "Workforce Programs" in content
    assert "Youth Services Funding" in content
    assert "Economic Development Programs" in content
    assert "Digital Equity Initiatives" in content
    assert "Community Development Programs" in content
    assert "Public-Sector Service Contracts" in content
    assert "RFPs / Procurement Opportunities" in content


def test_government_dashboard_entity_recommendations_render(client, government_project):
    project, user = government_project
    client.force_login(user)

    response = client.get(reverse("project-government", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert "City Government" in content
    assert "County Government" in content
    assert "Workforce Development Boards" in content
    assert "Economic Development Agencies" in content
    assert "Public School Districts" in content
    assert "Public Libraries" in content
    assert "Housing / Community Development Agencies" in content
    assert "Regional Planning Agencies" in content


def test_government_dashboard_checklist_shows_complete_and_missing_items(client, db):
    user = get_user_model().objects.create_user(
        username="government-dashboard-gaps",
        password="password",
    )
    organization = Organization.objects.create(
        name="Public Gap Works",
        website="https://public-gap.example",
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

    response = client.get(reverse("project-government", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert "Complete" in content
    assert "Missing" in content
    assert "Service Geography" in content
    assert "Program Description" in content
    assert "Target Population" in content
    assert "Outcomes / Impact" in content
    assert "Budget Range" in content
    assert "Public-Sector Partnership History" in content
    assert "Contract / Grant Readiness" in content
    assert "Local Contact Strategy" in content


def test_government_dashboard_actions_are_practical_and_gap_driven(client, government_project):
    project, user = government_project
    client.force_login(user)

    response = client.get(reverse("project-government", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert "Map city and county departments aligned with the mission and service geography." in content
    assert "Track local RFP and procurement portals for service contracts and pilot opportunities." in content
    assert "Use funding themes to decide which government lanes fit Primary Initiative first." in content
