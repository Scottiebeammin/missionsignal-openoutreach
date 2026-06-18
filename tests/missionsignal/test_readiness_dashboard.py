import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from openoutreach.funding.models import Opportunity
from openoutreach.funding.readiness import build_funding_readiness
from openoutreach.signals.demo import seed_missionsignal_demo
from openoutreach.signals.government import build_government_readiness
from openoutreach.signals.partnerships import build_partnership_readiness
from openoutreach.signals.readiness import (
    build_opportunity_pursuit_readiness,
    build_opportunity_pursuit_summary,
    build_organization_completeness,
    build_readiness_overview,
)
from openoutreach.signals.resources import build_resource_readiness


pytestmark = pytest.mark.django_db


@pytest.fixture
def readiness_project(db):
    user, _organization, project = seed_missionsignal_demo()
    return project, user


def _module_readiness(project):
    funding_criteria = project.funding_criteria
    funding = build_funding_readiness(project, funding_criteria)
    government = build_government_readiness(project, funding_criteria)
    resource = build_resource_readiness(project, funding_criteria)
    partnership = build_partnership_readiness(project, funding_criteria)
    return funding, government, resource, partnership


def test_organization_completeness_scoring(readiness_project):
    project, _user = readiness_project
    funding, government, resource, partnership = _module_readiness(project)

    completeness = build_organization_completeness(
        project,
        {
            "funding": funding,
            "government": government,
            "resource": resource,
            "partnership": partnership,
        },
    )

    assert 0 <= completeness.score <= 100
    assert completeness.level in ["Incomplete", "Emerging", "Developing", "Complete", "Advanced"]
    assert "Mission" in completeness.completed_areas
    assert "Programs" in completeness.completed_areas
    assert completeness.highest_leverage_missing_area
    assert any(area.label == "Funding Readiness" for area in completeness.areas)
    assert any(area.label == "Government Readiness" for area in completeness.areas)


def test_readiness_engine_scoring(readiness_project):
    project, _user = readiness_project
    funding, government, resource, partnership = _module_readiness(project)

    readiness = build_readiness_overview(project, funding, government, resource, partnership)

    assert 0 <= readiness.overall_score <= 100
    assert readiness.level in ["Emerging", "Developing", "Competitive", "Advanced"]
    assert len(readiness.dimensions) == 11
    assert any(dimension.label == "Mission Readiness" for dimension in readiness.dimensions)
    assert any(dimension.label == "Operational Readiness" for dimension in readiness.dimensions)
    assert any(dimension.label == "Document Readiness" for dimension in readiness.dimensions)
    assert any(dimension.label == "Evidence Readiness" for dimension in readiness.dimensions)
    assert any(dimension.label == "Submission Readiness" for dimension in readiness.dimensions)
    assert 0 <= readiness.document_readiness_score <= 100
    assert 0 <= readiness.evidence_readiness_score <= 100
    assert 0 <= readiness.submission_readiness_score <= 100
    assert readiness.strengths
    assert readiness.gaps
    assert readiness.recommended_actions


def test_opportunity_pursuit_readiness_scoring(readiness_project):
    project, _user = readiness_project
    opportunity = Opportunity.objects.get(name="Digital Equity Grant")

    pursuit = build_opportunity_pursuit_readiness(project, opportunity)

    assert 0 <= pursuit.score <= 100
    assert pursuit.level in ["Not Ready", "Needs Preparation", "Ready", "Strong Candidate"]
    assert pursuit.why_ready
    assert pursuit.why_not_ready
    assert pursuit.highest_leverage_improvement
    assert pursuit.missing_areas


def test_opportunity_pursuit_summary(readiness_project):
    project, _user = readiness_project

    summary = build_opportunity_pursuit_summary(project)

    assert 0 <= summary.average_score <= 100
    assert summary.ready_opportunities + summary.needs_preparation_opportunities == Opportunity.objects.count()
    assert summary.strongest_opportunity is not None
    assert summary.weakest_opportunity is not None


def test_project_member_can_view_readiness_dashboard(client, readiness_project):
    project, user = readiness_project
    client.force_login(user)

    response = client.get(reverse("project-readiness", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Readiness Engine V1" in content
    assert "Readiness Dashboard" in content
    assert "Overall Readiness" in content
    assert "Organization Completeness" in content
    assert "Organization Completeness Score" in content
    assert "Completed Areas" in content
    assert "Missing Areas" in content
    assert "Highest Leverage Missing Area" in content
    assert "Readiness Strengths" in content
    assert "Readiness Gaps" in content
    assert "Highest Leverage Actions" in content
    assert "Opportunity Pursuit Readiness Summary" in content
    assert "Document and Evidence Readiness" in content
    assert "Document readiness" in content
    assert "Evidence readiness" in content
    assert "Submission readiness" in content


def test_non_member_cannot_view_readiness_dashboard(client, readiness_project):
    project, _user = readiness_project
    outsider = get_user_model().objects.create_user(username="readiness-outsider")
    client.force_login(outsider)

    response = client.get(reverse("project-readiness", kwargs={"pk": project.pk}))

    assert response.status_code == 404


def test_dashboard_and_ecosystem_include_readiness_health(client, readiness_project):
    project, user = readiness_project
    client.force_login(user)

    dashboard = client.get(reverse("project-dashboard", kwargs={"pk": project.pk})).content.decode()
    ecosystem = client.get(reverse("project-ecosystem", kwargs={"pk": project.pk})).content.decode()

    assert "Readiness Health" in dashboard
    assert "Organization Completeness" in dashboard
    assert "Readiness Score" in dashboard
    assert "Top Readiness Gap" in dashboard
    assert "Top Readiness Action" in dashboard
    assert reverse("project-readiness", kwargs={"pk": project.pk}) in dashboard
    assert "Readiness Health" in ecosystem
    assert "Completeness Score" in ecosystem
    assert "Opportunity Readiness Average" in ecosystem
    assert reverse("project-readiness", kwargs={"pk": project.pk}) in ecosystem


def test_opportunity_workspace_displays_pursuit_readiness(client, readiness_project):
    project, user = readiness_project
    opportunity = Opportunity.objects.get(name="Digital Equity Grant")
    client.force_login(user)

    response = client.get(
        reverse("project-opportunity-workspace", kwargs={"pk": project.pk, "opportunity_id": opportunity.pk}),
    )
    content = response.content.decode()

    assert "Pursuit Readiness" in content
    assert "Readiness Details" in content
    assert "Improvement Opportunities" in content
    assert "Required Missing Areas" in content


def test_discovery_pipeline_and_matching_display_readiness(client, readiness_project):
    project, user = readiness_project
    client.force_login(user)

    discovery = client.get(reverse("project-discovery", kwargs={"pk": project.pk})).content.decode()
    pipeline = client.get(reverse("project-pipeline", kwargs={"pk": project.pk})).content.decode()
    matching = client.get(reverse("project-matches", kwargs={"pk": project.pk})).content.decode()

    assert "Pursuit Readiness" in discovery
    assert "Ready " in pipeline
    assert "Pursuit Readiness" in matching
    assert "Combined Opportunity Health" in matching
