import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from openoutreach.core.models import Organization, Project
from openoutreach.signals.analysis_service import analyze_project


@pytest.fixture
def resource_project(db):
    user = get_user_model().objects.create_user(
        username="resource-dashboard-member",
        password="password",
    )
    organization = Organization.objects.create(
        name="Resource Futures",
        website="https://resource-futures.example",
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


def test_project_member_can_view_resource_dashboard(client, resource_project):
    project, user = resource_project
    client.force_login(user)

    response = client.get(reverse("project-resources", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert response.status_code == 200
    assert "ResourceSignal Dashboard" in content
    assert "Resource Readiness Score" in content
    assert "Resource Opportunity Categories" in content
    assert "Recommended Resource Types" in content
    assert "Resource Readiness Checklist" in content
    assert "Recommended Resource Actions" in content
    assert "Resource Ecosystem Snapshot" in content
    assert "placeholder" not in content.casefold()


def test_non_member_cannot_view_resource_dashboard(client, resource_project):
    project, _ = resource_project
    outsider = get_user_model().objects.create_user(
        username="resource-dashboard-outsider",
        password="password",
    )
    client.force_login(outsider)

    response = client.get(reverse("project-resources", kwargs={"pk": project.pk}))

    assert response.status_code == 404


def test_resource_dashboard_categories_and_recommendations_render(client, resource_project):
    project, user = resource_project
    client.force_login(user)

    response = client.get(reverse("project-resources", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert "Technical Assistance" in content
    assert "Capacity Building Programs" in content
    assert "Nonprofit Accelerators" in content
    assert "Training &amp; Professional Development" in content
    assert "Volunteer Resources" in content
    assert "AmeriCorps &amp; National Service Programs" in content
    assert "Fellowships" in content
    assert "Shared Services" in content
    assert "Software &amp; Technology Resources" in content
    assert "Equipment &amp; Infrastructure Resources" in content
    assert "Technical Assistance Providers" in content
    assert "Capacity Building Organizations" in content
    assert "Nonprofit Support Centers" in content
    assert "Volunteer Networks" in content
    assert "AmeriCorps Programs" in content
    assert "University Support Programs" in content
    assert "Software Donation Programs" in content
    assert "Shared Service Organizations" in content
    assert "Equipment Assistance Programs" in content
    assert "Broadband &amp; Digital Access Programs" in content


def test_resource_dashboard_checklist_and_actions_render(client, resource_project):
    project, user = resource_project
    client.force_login(user)

    response = client.get(reverse("project-resources", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert "Mission Clarity" in content
    assert "Program Definition" in content
    assert "Service Geography" in content
    assert "Target Population" in content
    assert "Outcomes / Impact" in content
    assert "Budget Information" in content
    assert "Partnership Inventory" in content
    assert "Technology Needs" in content
    assert "Volunteer Strategy" in content
    assert "Capacity Building Strategy" in content
    assert "Complete" in content
    assert "Missing" in content
    assert "Document technology needs" in content
    assert "Create a volunteer engagement strategy" in content
    assert "Assess capacity-building opportunities" in content
    assert "Create an organizational resource plan" in content


def test_resource_dashboard_snapshot_and_navigation_render(client, resource_project):
    project, user = resource_project
    client.force_login(user)

    response = client.get(reverse("project-resources", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert "training, technical assistance, volunteers, technology, facilities, equipment, capacity-building programs, and shared services" in content
    assert reverse("project-mission-brief", kwargs={"pk": project.pk}) in content
    assert reverse("project-funding", kwargs={"pk": project.pk}) in content
    assert reverse("project-government", kwargs={"pk": project.pk}) in content
    assert reverse("project-ecosystem", kwargs={"pk": project.pk}) in content
