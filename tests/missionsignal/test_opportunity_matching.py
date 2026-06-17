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
    assert "Opportunity Matching V3" in content
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
    assert "Strong Match" in content
    assert "Moderate Match" in content
    assert "Match Confidence" in content
    assert "Workforce" in content
    assert "Digital Equity" in content or "Digital" in content
    assert "Cleveland geography alignment" in content
    assert "Nonprofit compatibility" in content
    assert match_level(76) == "Strong Match"
    assert match_level(60) == "Moderate Match"
    assert match_level(59) == "Weak Match"


def test_match_dashboard_renders_breakdowns_missing_factors_and_improvements(client, match_project):
    project, user = match_project
    client.force_login(user)

    response = client.get(reverse("project-matches", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert "Match Factors" in content
    assert "Geography Alignment" in content
    assert "Workforce Development Alignment" in content
    assert "Youth Alignment" in content
    assert "Missing Factors" in content
    assert "Outcomes not documented" in content
    assert "Budget range not provided" in content
    assert "Partnership inventory missing" in content
    assert "Funding history missing" in content
    assert "Improvement Opportunities" in content
    assert "Add measurable outcomes" in content
    assert "Add partner organizations" in content
    assert "Add annual budget range" in content
    assert "Add funding sources" in content
    assert "Add program impact evidence" in content
    assert "Current Match Score" in content
    assert "Potential Match Score" in content
    assert "Primary Recommendation" in content
    assert "Show More" in content
    assert "<summary>Why It Matches</summary>" in content
    assert "<summary>Missing Factors</summary>" in content
    assert "<summary>Improvement Opportunities</summary>" in content
    assert "View all matches" in content


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
    assert first.top_recommended[0].score == 100
    assert match_level(first.top_recommended[0].score) == first.top_recommended[0].level
    assert first.highest_score == 100
    assert first.strongest_category == "Funding"
    assert first.weakest_category == "Resource"
    assert first.highest_leverage_improvement == "Add measurable outcomes."
    assert first.readiness_signals == ["Outcomes", "Partnerships", "Budget", "Geography", "Beneficiaries"]
    assert first.top_gaps[0].label == "Outcomes not documented"
    assert first.top_gaps[0].count == 12


def test_weighted_scoring_and_ranking_order(match_project):
    project, _ = match_project
    funding_criteria = getattr(project, "funding_criteria", None)

    overview = build_opportunity_matches(project, funding_criteria)
    scores = [match.score for match in overview.top_recommended]

    assert scores == sorted(scores, reverse=True)
    assert overview.top_recommended[0].matching_factor_count >= overview.top_recommended[-1].matching_factor_count
    assert overview.categories[0].highest_score == 100
    assert overview.categories[0].lowest_score == 92
    assert overview.categories[2].average_score == 71
    assert overview.heatmap[0].label == "Funding"
    assert overview.heatmap[-1].label == "Resource"


def test_gap_analysis_heatmap_and_leverage_actions_render(client, match_project):
    project, user = match_project
    client.force_login(user)

    response = client.get(reverse("project-matches", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert "Top Match Gaps" in content
    assert "Outcomes not documented" in content
    assert "Partnership inventory missing" in content
    assert "Ecosystem Heatmap" in content
    assert "Funding" in content
    assert "Government" in content
    assert "Resource" in content
    assert "Partnership" in content
    assert "Highest Leverage Improvements" in content
    assert "Top 5 Actions That Would Improve The Most Matches" in content
    assert "Create partnership inventory." in content
    assert "Document annual budget range." in content


def test_expanded_categories_can_influence_inventory_matching(match_project):
    project, _ = match_project
    from openoutreach.funding.models import Opportunity
    from openoutreach.signals.matching import score_inventory_opportunity

    opportunity = Opportunity.objects.get(name="Inclusive Technology Access Resource Round")
    match = score_inventory_opportunity(project, opportunity, project.funding_criteria)

    assert "Disability" in opportunity.focus_areas
    assert "Digital Equity" in opportunity.focus_areas
    assert match.score >= 60
    assert any("Digital Equity" in factor or "Digital" in factor for factor in match.match_factors)


def test_ecosystem_dashboard_includes_match_summary(client, match_project):
    project, user = match_project
    client.force_login(user)

    response = client.get(reverse("project-ecosystem", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert "Opportunity Match Health" in content
    assert "Overall Match Score" in content
    assert "Total Opportunities" in content
    assert "Highest Match Category" in content
    assert "Weakest Match Category" in content
    assert "Highest Leverage Improvement" in content
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
