import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from openoutreach.signals.demo import seed_missionsignal_demo
from openoutreach.signals.matching import build_opportunity_matches, match_level


@pytest.fixture
def match_project(db):
    user, _organization, project = seed_missionsignal_demo()
    return project, user


def test_project_member_can_view_match_dashboard(client, match_project):
    project, user = match_project
    client.force_login(user)

    response = client.get(reverse("project-matches", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Opportunity Match Dashboard" in content
    assert "Overall Match Score" in content
    assert "Total Matches" in content.lower() or "total matches" in content
    assert "Match Categories" in content
    assert "Top Recommended Opportunities" in content


def test_non_member_cannot_view_match_dashboard(client, match_project):
    project, _ = match_project
    outsider = get_user_model().objects.create_user(
        username="match-dashboard-outsider",
        password="password",
    )
    client.force_login(outsider)

    response = client.get(reverse("project-matches", kwargs={"pk": project.pk}))

    assert response.status_code == 404


def test_match_dashboard_renders_all_match_categories(client, match_project):
    project, user = match_project
    client.force_login(user)

    response = client.get(reverse("project-matches", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert "Funding Matches" in content
    assert "Government Matches" in content
    assert "Resource Matches" in content
    assert "Partnership Matches" in content
    assert "Cuyahoga Community Foundation" in content
    assert "City of Cleveland Youth and Workforce Office" in content
    assert "Ohio Nonprofit Capacity Lab" in content
    assert "Cleveland Community College Career Pathways" in content


def test_match_dashboard_renders_scores_levels_and_reasons(client, match_project):
    project, user = match_project
    client.force_login(user)

    response = client.get(reverse("project-matches", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert "Excellent Match" in content
    assert "Workforce" in content
    assert "Digital Equity" in content or "Digital" in content
    assert "Cleveland geography alignment" in content
    assert "Nonprofit compatibility" in content
    assert match_level(76) == "Strong Match"
    assert match_level(58) == "Moderate Match"
    assert match_level(30) == "Weak Match"


def test_match_scoring_is_deterministic(match_project):
    project, _ = match_project
    funding_criteria = getattr(project, "funding_criteria", None)

    first = build_opportunity_matches(project, funding_criteria)
    second = build_opportunity_matches(project, funding_criteria)

    assert first.overall_score == second.overall_score
    assert first.total_matches == 12
    assert first.funding_count == 3
    assert first.government_count == 3
    assert first.resource_count == 3
    assert first.partnership_count == 3
    assert first.top_recommended[0].score >= 85
    assert match_level(first.top_recommended[0].score) == first.top_recommended[0].level


def test_ecosystem_dashboard_includes_match_summary(client, match_project):
    project, user = match_project
    client.force_login(user)

    response = client.get(reverse("project-ecosystem", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert "Match Summary" in content
    assert "Total Matches" in content
    assert "Funding Matches" in content
    assert "Government Matches" in content
    assert "Resource Matches" in content
    assert "Partnership Matches" in content
    assert "Open Opportunity Matching" in content
    assert reverse("project-matches", kwargs={"pk": project.pk}) in content


def test_match_dashboard_navigation_links(client, match_project):
    project, user = match_project
    client.force_login(user)

    response = client.get(reverse("project-matches", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert reverse("project-mission-brief", kwargs={"pk": project.pk}) in content
    assert reverse("project-funding", kwargs={"pk": project.pk}) in content
    assert reverse("project-government", kwargs={"pk": project.pk}) in content
    assert reverse("project-resources", kwargs={"pk": project.pk}) in content
    assert reverse("project-partnerships", kwargs={"pk": project.pk}) in content
    assert reverse("project-ecosystem", kwargs={"pk": project.pk}) in content
