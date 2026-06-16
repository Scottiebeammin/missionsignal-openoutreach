import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from openoutreach.core.models import Organization, Project
from openoutreach.signals.analysis_service import analyze_project


@pytest.fixture
def ecosystem_project(db):
    user = get_user_model().objects.create_user(
        username="ecosystem-dashboard-member",
        password="password",
    )
    organization = Organization.objects.create(
        name="Ecosystem Futures",
        website="https://ecosystem-futures.example",
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


def test_project_member_can_view_ecosystem_dashboard(client, ecosystem_project):
    project, user = ecosystem_project
    client.force_login(user)

    response = client.get(reverse("project-ecosystem", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Ecosystem Overview Dashboard" in content
    assert "Mission Brief" in content
    assert "FundingSignal" in content
    assert "GovernmentSignal" in content
    assert "ResourceSignal" in content
    assert "PartnershipSignal" in content


def test_non_member_cannot_view_ecosystem_dashboard(client, ecosystem_project):
    project, _ = ecosystem_project
    outsider = get_user_model().objects.create_user(
        username="ecosystem-dashboard-outsider",
        password="password",
    )
    client.force_login(outsider)

    response = client.get(reverse("project-ecosystem", kwargs={"pk": project.pk}))

    assert response.status_code == 404


def test_ecosystem_dashboard_score_and_summary_render(client, ecosystem_project):
    project, user = ecosystem_project
    client.force_login(user)

    response = client.get(reverse("project-ecosystem", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert "Opportunity Ecosystem Score" in content
    assert any(level in content for level in ["Emerging", "Developing", "Competitive", "Advanced"])
    assert "organizations operate within an opportunity ecosystem" in content.lower()
    assert "Funding" in content
    assert "Government" in content
    assert "Resources" in content
    assert "Partnerships" in content
    assert "Capacity" in content


def test_ecosystem_dashboard_roadmap_renders(client, ecosystem_project):
    project, user = ecosystem_project
    client.force_login(user)

    response = client.get(reverse("project-ecosystem", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert "Ecosystem Roadmap" in content
    assert "Completed" in content
    assert "Mission Brief" in content
    assert "FundingSignal" in content
    assert "GovernmentSignal" in content
    assert "Coming Soon" in content
    assert "ResourceSignal" in content
    assert "PartnershipSignal" in content
    assert "Future" in content
    assert "Opportunity Discovery Engine" in content
    assert "Monitoring Systems" in content
    assert "AI Opportunity Agents" in content


def test_ecosystem_dashboard_links_to_active_resource_signal(client, ecosystem_project):
    project, user = ecosystem_project
    client.force_login(user)

    response = client.get(reverse("project-ecosystem", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert reverse("project-resources", kwargs={"pk": project.pk}) in content
    assert "Resource readiness, non-funding categories, recommendations, checklist, and actions are available." in content


def test_mission_brief_links_to_ecosystem_dashboard(client, ecosystem_project):
    project, user = ecosystem_project
    client.force_login(user)

    response = client.get(reverse("project-mission-brief", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert "EcosystemSignal" in content
    assert reverse("project-ecosystem", kwargs={"pk": project.pk}) in content
