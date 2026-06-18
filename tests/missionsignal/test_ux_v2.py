import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from openoutreach.signals.demo import seed_missionsignal_demo


pytestmark = pytest.mark.django_db


@pytest.fixture
def ux_project(db):
    user, _organization, project = seed_missionsignal_demo()
    return project, user


def test_primary_navigation_is_workflow_based(client, ux_project):
    project, user = ux_project
    client.force_login(user)

    response = client.get(reverse("project-dashboard", kwargs={"pk": project.pk}))

    content = response.content.decode()
    assert "Dashboard" in content
    assert "Organization" in content
    assert "Opportunities" in content
    assert "Ecosystem" in content
    assert "Readiness" in content
    assert "Documents" in content
    assert "Evidence" in content
    assert "Celebrations" in content
    assert "Workspace Settings" in content
    assert reverse("project-organization", kwargs={"pk": project.pk}) in content
    assert reverse("project-opportunities", kwargs={"pk": project.pk}) in content
    assert reverse("project-readiness", kwargs={"pk": project.pk}) in content
    assert reverse("project-relationships", kwargs={"pk": project.pk}) in content
    assert reverse("project-documents", kwargs={"pk": project.pk}) in content
    assert reverse("project-evidence", kwargs={"pk": project.pk}) in content
    assert reverse("project-celebrations", kwargs={"pk": project.pk}) in content
    assert reverse("project-analysis-detail", kwargs={"pk": project.pk}) in content


def test_organization_workspace_groups_profile_work(client, ux_project):
    project, user = ux_project
    client.force_login(user)

    response = client.get(reverse("project-organization", kwargs={"pk": project.pk}))

    assert response.status_code == 200
    content = response.content.decode()
    assert "Organization Workspace" in content
    assert "Mission Brief" in content
    assert "Programs" in content
    assert "Outcomes" in content
    assert "Readiness Data" in content
    assert "Recommended Next Actions" in content


def test_opportunities_workspace_connects_discovery_matching_and_pipeline(client, ux_project):
    project, user = ux_project
    client.force_login(user)

    response = client.get(reverse("project-opportunities", kwargs={"pk": project.pk}))

    assert response.status_code == 200
    content = response.content.decode()
    assert "Opportunities Workspace" in content
    assert "Discovery" in content
    assert "Matches" in content
    assert "Pipeline" in content
    assert "Top Opportunities" in content
    assert "View All Opportunities" in content
    assert "Show More" in content
    assert "Opportunity Categories" in content
    assert "More Categories" in content
    assert "Show All Categories" in content
    assert "Collapse Categories" in content
    assert "Opportunity Health" in content
    assert "Upcoming Deadlines" in content
    assert "Opportunity Pipeline Summary" in content
    assert "Open full pipeline board" in content
    assert "Pipeline Health" in content
    assert "Active Lifecycle Opportunities" in content
    assert "Highest Priority Active" in content
    assert "Advanced Match Health" in content
    assert reverse("project-discovery", kwargs={"pk": project.pk}) in content
    assert reverse("project-matches", kwargs={"pk": project.pk}) in content
    assert reverse("project-pipeline", kwargs={"pk": project.pk}) in content


def test_workspace_routes_are_member_only(client, ux_project):
    project, _user = ux_project
    outsider = get_user_model().objects.create_user(username="ux-v2-outsider")
    client.force_login(outsider)

    assert client.get(reverse("project-organization", kwargs={"pk": project.pk})).status_code == 404
    assert client.get(reverse("project-opportunities", kwargs={"pk": project.pk})).status_code == 404
    assert client.get(reverse("project-pipeline", kwargs={"pk": project.pk})).status_code == 404


def test_ecosystem_workspace_tabs_group_signal_modules(client, ux_project):
    project, user = ux_project
    client.force_login(user)

    response = client.get(reverse("project-funding", kwargs={"pk": project.pk}))

    content = response.content.decode()
    assert "Ecosystem workspace tabs" in content
    assert reverse("project-ecosystem", kwargs={"pk": project.pk}) in content
    assert reverse("project-funding", kwargs={"pk": project.pk}) in content
    assert reverse("project-government", kwargs={"pk": project.pk}) in content
    assert reverse("project-resources", kwargs={"pk": project.pk}) in content
    assert reverse("project-partnerships", kwargs={"pk": project.pk}) in content
