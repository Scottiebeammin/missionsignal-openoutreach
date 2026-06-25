import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from openoutreach.signals.demo import seed_missionsignal_demo


pytestmark = pytest.mark.django_db


@pytest.fixture
def dashboard_project(db):
    user, _organization, project = seed_missionsignal_demo()
    return project, user


def test_project_member_can_view_executive_dashboard(client, dashboard_project):
    project, user = dashboard_project
    client.force_login(user)

    response = client.get(reverse("project-dashboard", kwargs={"pk": project.pk}))

    assert response.status_code == 200
    content = response.content.decode()
    assert "Anansi Atlas" in content
    assert "Executive Command Center" in content
    assert "Forecast Value" in content
    assert "Top 3 Strategic Moves" in content
    assert "Single highest-leverage action for leadership attention." in content
    assert "Opportunity To Watch" in content
    assert "Start Here" in content
    assert "Readiness" in content
    assert "Relationships" in content


def test_executive_dashboard_renders_celebration_area(client, dashboard_project):
    project, user = dashboard_project
    client.force_login(user)

    response = client.get(reverse("project-dashboard", kwargs={"pk": project.pk}))

    content = response.content.decode()
    assert "Wins Across the Web" in content
    assert "Latest celebrations and stories of mission progress." in content
    assert "Environmental Justice Partnership" in content
    assert "Food Security Milestone" in content
    assert "Veterans Support Initiative" in content
    assert "View All" in content
    assert reverse("project-celebrations", kwargs={"pk": project.pk}) in content


def test_non_member_cannot_view_executive_dashboard(client, dashboard_project):
    project, _user = dashboard_project
    outsider = get_user_model().objects.create_user(username="dashboard-outsider")
    client.force_login(outsider)

    response = client.get(reverse("project-dashboard", kwargs={"pk": project.pk}))

    assert response.status_code == 404


def test_executive_dashboard_renders_kpi_bar(client, dashboard_project):
    project, user = dashboard_project
    client.force_login(user)

    response = client.get(reverse("project-dashboard", kwargs={"pk": project.pk}))

    content = response.content.decode()
    assert "Readiness" in content
    assert "Relationship Health" in content
    assert "Pathway Health" in content
    assert "Forecast Value" in content


def test_executive_dashboard_renders_intelligence_grid(client, dashboard_project):
    project, user = dashboard_project
    client.force_login(user)

    response = client.get(reverse("project-dashboard", kwargs={"pk": project.pk}))

    content = response.content.decode()
    assert "Forecast" in content
    assert "Active Pipeline" in content
    assert "Upcoming Deadlines" in content


def test_executive_dashboard_renders_start_here_flow(client, dashboard_project):
    project, user = dashboard_project
    client.force_login(user)

    response = client.get(reverse("project-dashboard", kwargs={"pk": project.pk}))

    content = response.content.decode()
    assert "Start Here" in content
    assert "Opportunity Web" in content
    assert "Snapshot" in content
    assert "Pathways" in content
    assert "Pipeline" in content


def test_executive_dashboard_workspace_nav_links(client, dashboard_project):
    project, user = dashboard_project
    client.force_login(user)

    response = client.get(reverse("project-dashboard", kwargs={"pk": project.pk}))

    content = response.content.decode()
    assert "All Workspaces" in content
    assert reverse("project-mission-brief", kwargs={"pk": project.pk}) in content
    assert reverse("project-funding", kwargs={"pk": project.pk}) in content
    assert reverse("project-government", kwargs={"pk": project.pk}) in content
    assert reverse("project-discovery", kwargs={"pk": project.pk}) in content
    assert reverse("project-pipeline", kwargs={"pk": project.pk}) in content
    assert reverse("project-ecosystem", kwargs={"pk": project.pk}) in content
    assert reverse("project-readiness", kwargs={"pk": project.pk}) in content
    assert reverse("project-relationships", kwargs={"pk": project.pk}) in content
    assert reverse("project-celebrations", kwargs={"pk": project.pk}) in content


def test_executive_dashboard_no_accordion_elements(client, dashboard_project):
    project, user = dashboard_project
    client.force_login(user)

    response = client.get(reverse("project-dashboard", kwargs={"pk": project.pk}))

    content = response.content.decode()
    assert "<details" not in content
    assert "<summary>" not in content
