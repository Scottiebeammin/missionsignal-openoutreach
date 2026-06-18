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
    assert "Anansi Atlas Executive Dashboard" in content
    assert "Anansi Atlas" in content
    assert "The Web of Opportunity" in content
    assert "anansiatlas.com" in content
    assert "Scott Foundry Group LLC" in content
    assert "Ecosystem Score" in content
    assert "Overall Match Score" in content
    assert "Last Analysis Date" in content
    assert "Score Transparency" in content
    assert "Readiness Score Transparency" in content
    assert "Match Score Transparency" in content
    assert "Forecast Health Transparency" in content
    assert "Relationship Health Transparency" in content
    assert "Opportunity Command Center" not in content


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
    assert "View All Celebrations" in content
    assert reverse("project-celebrations", kwargs={"pk": project.pk}) in content


def test_non_member_cannot_view_executive_dashboard(client, dashboard_project):
    project, _user = dashboard_project
    outsider = get_user_model().objects.create_user(username="dashboard-outsider")
    client.force_login(outsider)

    response = client.get(reverse("project-dashboard", kwargs={"pk": project.pk}))

    assert response.status_code == 404


def test_executive_dashboard_renders_kpi_cards(client, dashboard_project):
    project, user = dashboard_project
    client.force_login(user)

    response = client.get(reverse("project-dashboard", kwargs={"pk": project.pk}))

    content = response.content.decode()
    assert "Executive KPI Cards" in content
    assert "Funding Score" in content
    assert "Government Score" in content
    assert "Resource Score" in content
    assert "Partnership Score" in content


def test_executive_dashboard_renders_opportunity_summaries(client, dashboard_project):
    project, user = dashboard_project
    client.force_login(user)

    response = client.get(reverse("project-dashboard", kwargs={"pk": project.pk}))

    content = response.content.decode()
    assert "Total Opportunities" in content
    assert "Active Opportunities" in content
    assert "High Priority Opportunities" in content
    assert "Applied Opportunities" in content
    assert "Won Opportunities" in content
    assert "Opportunity Pipeline Snapshot" in content
    assert "Opportunity Pipeline Summary" in content
    assert "Opportunity Work Summary" in content
    assert "Open Tasks" in content
    assert "Overdue Tasks" in content
    assert "Next Critical Deadline" in content
    assert "Opportunities in Drafting" in content
    assert "Pipeline Health Score" in content
    assert "Active Lifecycle Opportunities" in content
    assert "Highest Priority Active Opportunity" in content
    assert "Upcoming Deadlines" in content
    assert "Discovered" in content
    assert "Qualified" in content
    assert "Pursuing" in content
    assert "Submitted" in content
    assert "Awarded" in content
    assert "Monitoring" in content
    assert "Interested" in content
    assert "Applied" in content
    assert "Won" in content
    assert "Archived" in content


def test_executive_dashboard_renders_match_and_discovery_health(client, dashboard_project):
    project, user = dashboard_project
    client.force_login(user)

    response = client.get(reverse("project-dashboard", kwargs={"pk": project.pk}))

    content = response.content.decode()
    assert "Opportunity Match Health" in content
    assert "Excellent Matches" in content
    assert "Strong Matches" in content
    assert "Moderate Matches" in content
    assert "Weak Matches" in content
    assert "Discovery Health" in content
    assert "Total Source Organizations" in content
    assert "Opportunity Categories" in content
    assert "Upcoming Deadlines" in content


def test_executive_dashboard_navigation_and_view_switcher_render(client, dashboard_project):
    project, user = dashboard_project
    client.force_login(user)

    response = client.get(reverse("project-dashboard", kwargs={"pk": project.pk}))

    content = response.content.decode()
    assert "Dashboard View" in content
    assert "Table View" in content
    assert "Chart View" in content
    assert reverse("project-dashboard", kwargs={"pk": project.pk}) in content
    assert reverse("project-mission-brief", kwargs={"pk": project.pk}) in content
    assert reverse("project-funding", kwargs={"pk": project.pk}) in content
    assert reverse("project-government", kwargs={"pk": project.pk}) in content
    assert reverse("project-resources", kwargs={"pk": project.pk}) in content
    assert reverse("project-partnerships", kwargs={"pk": project.pk}) in content
    assert reverse("project-discovery", kwargs={"pk": project.pk}) in content
    assert reverse("project-matches", kwargs={"pk": project.pk}) in content
    assert reverse("project-pipeline", kwargs={"pk": project.pk}) in content
    assert reverse("project-ecosystem", kwargs={"pk": project.pk}) in content
    assert reverse("project-readiness", kwargs={"pk": project.pk}) in content
    assert reverse("project-relationships", kwargs={"pk": project.pk}) in content
    assert reverse("project-documents", kwargs={"pk": project.pk}) in content
    assert reverse("project-evidence", kwargs={"pk": project.pk}) in content
    assert reverse("project-celebrations", kwargs={"pk": project.pk}) in content
    assert "Workspace Settings" in content


def test_executive_dashboard_renders_chart_ready_sections(client, dashboard_project):
    project, user = dashboard_project
    client.force_login(user)

    response = client.get(reverse("project-dashboard", kwargs={"pk": project.pk}))

    content = response.content.decode()
    assert "Visualization Layer" in content
    assert "Funding vs Government vs Resource vs Partnership Scores" in content
    assert "Opportunity Category Distribution" in content
    assert "Opportunity Status Distribution" in content
    assert "Priority Distribution" in content
