import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from openoutreach.core.models import Organization, Project
from openoutreach.signals.analysis_service import analyze_project


@pytest.fixture
def partnership_project(db):
    user = get_user_model().objects.create_user(
        username="partnership-dashboard-member",
        password="password",
    )
    organization = Organization.objects.create(
        name="Partnership Futures",
        website="https://partnership-futures.example",
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


def test_project_member_can_view_partnership_dashboard(client, partnership_project):
    project, user = partnership_project
    client.force_login(user)

    response = client.get(reverse("project-partnerships", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Partnerships Dashboard" in content
    assert "Partnership Readiness Score" in content
    assert "Partnership Categories" in content
    assert "Recommended Partner Types" in content
    assert "Partnership Readiness Checklist" in content
    assert "Recommended Partnership Actions" in content
    assert "Partnership Ecosystem Snapshot" in content
    assert "placeholder" not in content.casefold()


def test_non_member_cannot_view_partnership_dashboard(client, partnership_project):
    project, _ = partnership_project
    outsider = get_user_model().objects.create_user(
        username="partnership-dashboard-outsider",
        password="password",
    )
    client.force_login(outsider)

    response = client.get(reverse("project-partnerships", kwargs={"pk": project.pk}))

    assert response.status_code == 404


def test_partnership_dashboard_categories_and_recommendations_render(client, partnership_project):
    project, user = partnership_project
    client.force_login(user)

    response = client.get(reverse("project-partnerships", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert "Nonprofit Collaborators" in content
    assert "Universities &amp; Colleges" in content
    assert "Community Colleges" in content
    assert "Workforce Boards" in content
    assert "Local Government Agencies" in content
    assert "Public Libraries" in content
    assert "School Districts" in content
    assert "Healthcare Organizations" in content
    assert "Corporate Partners" in content
    assert "Foundations" in content
    assert "Faith-Based Organizations" in content
    assert "Community-Based Organizations" in content
    assert "Workforce Development Boards" in content
    assert "Corporate Social Impact Teams" in content
    assert "Community Foundations" in content
    assert "Nonprofit Coalitions" in content
    assert "Healthcare / Human Services Providers" in content
    assert "Faith-Based Networks" in content


def test_partnership_dashboard_checklist_and_actions_render(client, partnership_project):
    project, user = partnership_project
    client.force_login(user)

    response = client.get(reverse("project-partnerships", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert "Mission Clarity" in content
    assert "Program Definition" in content
    assert "Service Geography" in content
    assert "Target Population" in content
    assert "Outcomes / Impact" in content
    assert "Existing Partnerships" in content
    assert "Partnership Goals" in content
    assert "Collaboration Capacity" in content
    assert "One-Page Partnership Brief" in content
    assert "Local Contact Strategy" in content
    assert "Complete" in content
    assert "Missing" in content
    assert "Create a one-page partnership brief" in content
    assert "Define partnership goals for each program" in content
    assert "Build a local contact strategy" in content


def test_partnership_dashboard_snapshot_and_navigation_render(client, partnership_project):
    project, user = partnership_project
    client.force_login(user)

    response = client.get(reverse("project-partnerships", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert "expand reach, credibility, referral pathways, service delivery capacity, funding competitiveness, program sustainability, and community trust" in content
    assert reverse("project-mission-brief", kwargs={"pk": project.pk}) in content
    assert reverse("project-funding", kwargs={"pk": project.pk}) in content
    assert reverse("project-government", kwargs={"pk": project.pk}) in content
    assert reverse("project-resources", kwargs={"pk": project.pk}) in content
    assert reverse("project-ecosystem", kwargs={"pk": project.pk}) in content
