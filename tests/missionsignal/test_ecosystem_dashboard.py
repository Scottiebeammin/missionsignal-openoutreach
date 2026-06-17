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
    assert "Opportunity Ecosystem Dashboard" in content
    assert "EcosystemSignal V1" in content
    assert "Mission Brief" in content
    assert "FundingSignal" in content
    assert "GovernmentSignal" in content
    assert "ResourceSignal" in content
    assert "PartnershipSignal" in content
    assert "Pipeline" in content


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
    assert "MissionSignal views organizations through an opportunity ecosystem" in content
    for item in ["Funding", "Government", "Resources", "Partnerships", "Capacity", "Risks and constraints"]:
        assert item in content


def test_ecosystem_dashboard_signal_scorecards_render(client, ecosystem_project):
    project, user = ecosystem_project
    client.force_login(user)

    response = client.get(reverse("project-ecosystem", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert "Signal Scorecards" in content
    assert "Mission profile, project narrative, geography, beneficiaries, and readiness gaps." in content
    assert "Funding themes, funder types, Local Government lanes, checklist, and actions." in content
    assert "Public-sector lanes, government entity types, checklist, and actions." in content
    assert "Non-funding resources, capacity supports, checklist, and actions." in content
    assert "Partner categories, partner recommendations, checklist, and actions." in content
    assert content.count("Active") >= 5


def test_ecosystem_dashboard_collapses_type_and_category_lists(client, ecosystem_project):
    project, user = ecosystem_project
    client.force_login(user)

    response = client.get(reverse("project-ecosystem", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert "Executive Ecosystem Signals" in content
    assert "Strongest Signal" in content
    assert "Weakest Signal" in content
    assert "Highest Leverage Action" in content
    assert "Opportunity Health" in content
    assert "Ecosystem Type Summaries" in content
    assert "Funder Types" in content
    assert "More Funder Types" in content
    assert "Government Entity Types" in content
    assert "More Government Entities" in content
    assert "Resource Types" in content
    assert "More Resource Types" in content
    assert "Resource Categories" in content
    assert "Partnership Categories" in content
    assert "More Categories" in content
    assert "Show All" in content
    assert "Show All Categories" in content
    assert "Collapse" in content


def test_ecosystem_dashboard_strengths_and_gaps_render(client, ecosystem_project):
    project, user = ecosystem_project
    client.force_login(user)

    response = client.get(reverse("project-ecosystem", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert "Ecosystem Strengths" in content
    assert "Clear mission" in content
    assert "Defined programs" in content
    assert "Geographic focus" in content
    assert "Target population identified" in content
    assert "Strong government alignment" in content
    assert "Strong funding theme alignment" in content
    assert "Ecosystem Gaps" in content
    assert "Technology Needs missing" in content
    assert "Volunteer Strategy missing" in content
    assert "Capacity Building Strategy missing" in content
    assert "Partnership Goals missing" in content


def test_ecosystem_dashboard_priority_areas_and_actions_render(client, ecosystem_project):
    project, user = ecosystem_project
    client.force_login(user)

    response = client.get(reverse("project-ecosystem", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert "Priority Opportunity Areas" in content
    assert "Funding Readiness" in content
    assert "Government Engagement" in content
    assert "Resource Development" in content
    assert "Partnership Development" in content
    assert "Capacity Building" in content
    assert "Outcomes Measurement" in content
    assert "Recommended Ecosystem Actions" in content
    assert "Create a one-page partnership and government engagement brief." in content
    assert "Create a resource needs inventory." in content


def test_ecosystem_dashboard_links_to_all_signal_modules(client, ecosystem_project):
    project, user = ecosystem_project
    client.force_login(user)

    response = client.get(reverse("project-ecosystem", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert reverse("project-mission-brief", kwargs={"pk": project.pk}) in content
    assert reverse("project-funding", kwargs={"pk": project.pk}) in content
    assert reverse("project-government", kwargs={"pk": project.pk}) in content
    assert reverse("project-resources", kwargs={"pk": project.pk}) in content
    assert reverse("project-partnerships", kwargs={"pk": project.pk}) in content
    assert reverse("project-matches", kwargs={"pk": project.pk}) in content
    assert reverse("project-pipeline", kwargs={"pk": project.pk}) in content


def test_ecosystem_dashboard_includes_lifecycle_health(client, ecosystem_project):
    project, user = ecosystem_project
    client.force_login(user)

    response = client.get(reverse("project-ecosystem", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert "Lifecycle Health" in content
    assert "Pipeline Health" in content
    assert "Pipeline Stage Distribution" in content
    assert "Active Opportunities" in content
    assert "Submitted Opportunities" in content
    assert "Awarded Opportunities" in content
    assert "Open Pipeline" in content


def test_mission_brief_links_to_ecosystem_dashboard(client, ecosystem_project):
    project, user = ecosystem_project
    client.force_login(user)

    response = client.get(reverse("project-mission-brief", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert "EcosystemSignal" in content
    assert reverse("project-ecosystem", kwargs={"pk": project.pk}) in content
