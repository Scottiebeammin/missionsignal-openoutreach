import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from openoutreach.funding.models import Opportunity
from openoutreach.signals.demo import seed_missionsignal_demo
from openoutreach.signals.discovery import build_discovery_overview


@pytest.fixture
def discovery_project(db):
    user, _organization, project = seed_missionsignal_demo()
    return project, user


def test_project_member_can_view_discovery_dashboard(client, discovery_project):
    project, user = discovery_project
    client.force_login(user)

    response = client.get(reverse("project-discovery", kwargs={"pk": project.pk}))

    assert response.status_code == 200
    content = response.content.decode()
    assert "Discovery Engine V1" in content
    assert "Opportunity Inventory" in content
    assert "Total Opportunities" in content
    assert "Active Opportunities" in content


def test_non_member_cannot_view_discovery_dashboard(client, discovery_project):
    project, _ = discovery_project
    outsider = get_user_model().objects.create_user(username="discovery-outsider")
    client.force_login(outsider)

    response = client.get(reverse("project-discovery", kwargs={"pk": project.pk}))

    assert response.status_code == 404


def test_discovery_inventory_and_readiness_render(client, discovery_project):
    project, user = discovery_project
    client.force_login(user)

    response = client.get(reverse("project-discovery", kwargs={"pk": project.pk}))

    content = response.content.decode()
    assert "Opportunity Inventory Summary" in content
    assert "Grants" in content
    assert "Government" in content
    assert "Resources" in content
    assert "Partnerships" in content
    assert "Digital Equity Grant" in content
    assert "Workforce Development Grant" in content
    assert "Youth Technology Initiative" in content
    assert "Community Partnership Program" in content
    assert "Capacity Building Resource Program" in content
    assert "Match Score" in content
    assert "Why It Matches" in content
    assert "Strong Match" in content or "Excellent Match" in content


def test_discovery_demo_records_are_deterministic(discovery_project):
    project, _user = discovery_project
    first = build_discovery_overview(project, project.funding_criteria)
    second = build_discovery_overview(project, project.funding_criteria)

    assert first.total_opportunities == 5
    assert first.active_opportunities == 4
    assert first.best_opportunity_category == second.best_opportunity_category
    assert [item.opportunity.name for item in first.top_opportunities] == [
        item.opportunity.name for item in second.top_opportunities
    ]
    assert Opportunity.objects.filter(name="Digital Equity Grant").count() == 1


def test_ecosystem_dashboard_includes_discovery_summary(client, discovery_project):
    project, user = discovery_project
    client.force_login(user)

    response = client.get(reverse("project-ecosystem", kwargs={"pk": project.pk}))

    content = response.content.decode()
    assert "Discovery Engine Summary" in content
    assert "Total Opportunities" in content
    assert "Active Opportunities" in content
    assert "Best Opportunity Category" in content
    assert "Open Discovery Engine" in content
    assert reverse("project-discovery", kwargs={"pk": project.pk}) in content


def test_discovery_navigation_links_render(client, discovery_project):
    project, user = discovery_project
    client.force_login(user)

    response = client.get(reverse("project-discovery", kwargs={"pk": project.pk}))

    content = response.content.decode()
    assert reverse("project-mission-brief", kwargs={"pk": project.pk}) in content
    assert reverse("project-funding", kwargs={"pk": project.pk}) in content
    assert reverse("project-government", kwargs={"pk": project.pk}) in content
    assert reverse("project-resources", kwargs={"pk": project.pk}) in content
    assert reverse("project-partnerships", kwargs={"pk": project.pk}) in content
    assert reverse("project-ecosystem", kwargs={"pk": project.pk}) in content
    assert reverse("project-matches", kwargs={"pk": project.pk}) in content
