import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from openoutreach.signals.demo import seed_missionsignal_demo
from openoutreach.signals.discovery import build_discovery_overview
from openoutreach.signals.opportunity_web import build_opportunity_web


pytestmark = pytest.mark.django_db


@pytest.fixture
def opportunity_web_project(db):
    user, _organization, project = seed_missionsignal_demo()
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
    assert "Opportunity Web V2" in content
    assert "The Web of Opportunity" in content
    assert "Executive Ecosystem Summary" in content
    assert "Ecosystem Health" in content
    assert "Strongest Asset" in content
    assert "Biggest Constraint" in content
    assert "Highest Leverage Relationship" in content
    assert "Highest Leverage Opportunity" in content
    assert "Web of Opportunity Story" in content
    assert "Mission creates the center" in content
    assert "Top 3 Strategic Moves" in content
    assert "Opportunity Web Insights" in content
    assert "Opportunity Insight" in content
    assert "Relationship Insight" in content
    assert "Readiness Insight" in content
    assert "Ecosystem Insight" in content
    assert "Snapshot is the executive interpretation of this web" in content
    assert "Connected Ecosystem Detail" in content
    assert "Mission Node" in content
    assert "Funders Node" in content
    assert "Partners Node" in content
    assert "Contacts Node" in content
    assert "Resources Node" in content
    assert "Opportunities Node" in content
    assert "Outcomes Node" in content
    assert "Opportunity Gaps" in content
    assert "Highest Leverage Actions" in content
    assert "Relationship Health" in content
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
    assert "Opportunity Web Summary" in dashboard
    assert "View Opportunity Web" in dashboard
    assert web_url in dashboard
    assert "Opportunity Web" in ecosystem
    assert "View Opportunity Web" in ecosystem
    assert web_url in ecosystem
