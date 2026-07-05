import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from openoutreach.funding.models import Opportunity
from openoutreach.signals.demo import seed_missionsignal_demo
from openoutreach.signals.discovery import build_discovery_overview
from openoutreach.signals.opportunity_web import build_opportunity_web


pytestmark = pytest.mark.django_db


@pytest.fixture
def opportunity_web_project(db):
    user, _organization, project = seed_missionsignal_demo()
    # The demo seed builds a global inventory (project=None); project pages read
    # project-scoped rows, so adopt the inventory into the project like a real
    # discovery run would.
    Opportunity.objects.filter(project__isnull=True).update(project=project)
    return project, user


def test_opportunity_web_overview_builds_nodes_and_gaps(opportunity_web_project):
    project, _user = opportunity_web_project
    discovery = build_discovery_overview(project, project.funding_criteria)

    web = build_opportunity_web(project, discovery)

    labels = [node.label for node in web.nodes]
    assert labels == [
        "Mission",
        "Funders",
        "Partners",
        "Contacts",
        "Resources",
        "Opportunities",
        "Outcomes",
    ]
    assert web.relationship_health_score > 0
    assert web.active_opportunities > 0
    assert web.forecast_value > 0
    assert web.opportunity_gaps
    assert web.highest_leverage_actions
    assert web.ecosystem_health > 0
    assert web.ecosystem_health_level
    assert web.strongest_asset
    assert web.biggest_constraint
    assert web.highest_leverage_relationship
    assert web.highest_leverage_opportunity
    assert web.opportunity_insight
    assert web.relationship_insight
    assert web.readiness_insight
    assert web.ecosystem_insight
    assert len(web.strategic_moves) == 3


def test_project_member_can_view_opportunity_web_page(client, opportunity_web_project):
    project, user = opportunity_web_project
    client.force_login(user)

    response = client.get(reverse("project-opportunity-web", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert response.status_code == 200
    assert "<h1>Opportunity Web</h1>" in content
    assert "The Web of Opportunity" in content
    assert "What is the Opportunity Web?" in content
    assert "Ecosystem Summary" in content
    assert "Ecosystem Health" in content
    assert "Strongest Asset" in content
    assert "Biggest Constraint" in content
    assert "Top Move Right Now" in content
    assert "Highest-leverage relationship:" in content
    assert "Highest-leverage opportunity:" in content
    assert "Strategic Moves" in content
    assert "Opportunity Insight" in content
    assert "Relationship Insight" in content
    assert "Readiness Insight" in content
    assert "Ecosystem Insight" in content
    assert "Open Full Snapshot" in content
    assert "Ecosystem Breakdown" in content
    assert "Strengths" in content
    assert "Gaps to close" in content
    assert "Opportunity Gaps" in content
    assert "Relationship health" in content
    assert "Active opportunities" in content
    assert "Forecast value" in content
    assert "Evidence indicators" in content


def test_non_member_cannot_view_opportunity_web_page(client, opportunity_web_project):
    project, _user = opportunity_web_project
    outsider = get_user_model().objects.create_user(username="opportunity-web-outsider")
    client.force_login(outsider)

    response = client.get(reverse("project-opportunity-web", kwargs={"pk": project.pk}))

    assert response.status_code == 404


def test_dashboard_and_ecosystem_link_to_opportunity_web(client, opportunity_web_project):
    project, user = opportunity_web_project
    client.force_login(user)

    dashboard = client.get(reverse("project-dashboard", kwargs={"pk": project.pk})).content.decode()
    ecosystem = client.get(reverse("project-ecosystem", kwargs={"pk": project.pk})).content.decode()

    web_url = reverse("project-opportunity-web", kwargs={"pk": project.pk})
    assert "Opportunity Web" in dashboard
    assert "Full ecosystem map" in dashboard
    assert web_url in dashboard
    assert "Opportunity Web" in ecosystem
    assert "View Opportunity Web" in ecosystem
    assert web_url in ecosystem
