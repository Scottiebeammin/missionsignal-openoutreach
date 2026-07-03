import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from openoutreach.signals.demo import seed_missionsignal_demo
from openoutreach.signals.matching import build_opportunity_matches, match_level


@pytest.fixture
def match_project(db):
    user, _organization, project = seed_missionsignal_demo()
    return project, user


@pytest.fixture
def real_reference_records(match_project):
    """Real-domain records for each category — demo (example.*) entities are
    excluded from client matching, so render tests assert against these."""
    from openoutreach.funding.models import (
        Funder, GovernmentEntity, PartnerOrganization, ResourceProvider,
    )
    project, _user = match_project
    geo = ["Cleveland", "Cuyahoga", "Ohio"]
    focus = ["Workforce Development", "Youth Development", "Education"]
    funder = Funder.objects.create(
        name="Lakeshore Youth Opportunity Fund", website="https://lakeshoreyouthfund.org",
        geography=geo, focus_areas=focus, beneficiaries=["Youth"], active=True,
    )
    gov = GovernmentEntity.objects.create(
        name="Cleveland Office of Youth Workforce", website="https://clevelandohio.gov",
        geography=geo, focus_areas=focus, opportunity_lanes=["Workforce grants"], active=True,
    )
    resource = ResourceProvider.objects.create(
        name="Great Lakes Nonprofit Support Center", website="https://glnonprofitsupport.org",
        geography=geo, focus_areas=focus, active=True,
    )
    partner = PartnerOrganization.objects.create(
        name="Cleveland Career Pathways Alliance", website="https://clecareerpathways.org",
        geography=geo, focus_areas=focus, beneficiaries=["Youth"],
        collaboration_opportunities=["Workforce referrals"], active=True,
    )
    return funder, gov, resource, partner


def test_project_member_can_view_match_dashboard(client, match_project):
    project, user = match_project
    client.force_login(user)

    response = client.get(reverse("project-matches", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Matches · Supporting Tool" in content
    assert "Review pathway fit." in content
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


def test_match_dashboard_renders_all_match_categories(client, match_project, real_reference_records):
    project, user = match_project
    client.force_login(user)

    response = client.get(reverse("project-matches", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert "Funding Matches" in content
    assert "Government Matches" in content
    assert "Resource Matches" in content
    assert "Partnership Matches" in content
    for record in real_reference_records:
        assert record.name in content


def test_match_dashboard_renders_scores_levels_and_reasons(client, match_project):
    project, user = match_project
    client.force_login(user)

    response = client.get(reverse("project-matches", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert "Match Confidence" in content
    assert "Workforce" in content
    # at least one confidence band must render for the top matches
    assert any(level in content for level in ("Excellent Match", "Strong Match", "Moderate Match"))
    assert "Why It Matches" in content
    assert match_level(76) == "Strong Match"
    assert match_level(60) == "Moderate Match"
    assert match_level(59) == "Weak Match"


def test_match_dashboard_renders_breakdowns_missing_factors_and_improvements(client, match_project):
    project, user = match_project
    client.force_login(user)

    response = client.get(reverse("project-matches", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert "Match Factors" in content
    assert "Score Transparency" in content
    assert "Match Score Transparency" in content
    assert "Score Contributors" in content
    assert "Score Gaps" in content
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
    assert "Suggested Lifecycle Stage" in content
    assert "Current Lifecycle Status" in content
    assert "Not in pipeline" in content
    assert "Owner:" in content
    assert "Unassigned" in content
    assert "Suggested Next Action" in content
    assert "Review eligibility" in content
    assert "Discovered" in content
    assert "Primary Recommendation" in content
    assert "Why It Matches" in content
    assert "Show all" in content or "all matches" in content.lower()


def test_match_scoring_is_deterministic(match_project):
    project, _ = match_project
    funding_criteria = getattr(project, "funding_criteria", None)

    first = build_opportunity_matches(project, funding_criteria)
    second = build_opportunity_matches(project, funding_criteria)

    assert first.overall_score == second.overall_score
    # Demo-seeded resource/partner providers use example.* domains and are now
    # excluded from matching (demo fiction never reaches clients), so only the
    # funding + government entities with real-looking data participate here.
    assert first.total_matches == 12
    assert first.funding_count == 9
    assert first.government_count == 3
    assert first.resource_count == 0
    assert first.partnership_count == 0
    assert first.top_recommended[0].score == 100
    assert match_level(first.top_recommended[0].score) == first.top_recommended[0].level
    assert first.highest_score == 100
    assert first.strongest_category == "Government"
    assert first.weakest_category == "Partnership"
    assert first.highest_leverage_improvement == "Add measurable outcomes."
    assert first.readiness_signals == ["Outcomes", "Partnerships", "Budget", "Geography", "Beneficiaries"]
    assert first.top_gaps[0].label == "Outcomes not documented"
    assert first.top_gaps[0].count == first.total_matches
    assert first.top_recommended[0].suggested_lifecycle_stage == "Discovered"
    assert first.top_recommended[0].current_lifecycle_status == "Not in pipeline"
    assert first.top_recommended[0].owner_label == "Unassigned"
    assert first.top_recommended[0].suggested_next_action == "Review eligibility"


def test_weighted_scoring_and_ranking_order(match_project):
    project, _ = match_project
    funding_criteria = getattr(project, "funding_criteria", None)

    overview = build_opportunity_matches(project, funding_criteria)
    scores = [match.score for match in overview.top_recommended]

    assert scores == sorted(scores, reverse=True)
    assert overview.top_recommended[0].matching_factor_count >= overview.top_recommended[-1].matching_factor_count
    assert overview.categories[0].highest_score == 100
    assert overview.categories[0].lowest_score < overview.categories[0].highest_score
    for category in overview.categories:
        assert category.lowest_score <= category.average_score <= category.highest_score
    heatmap_labels = {cell.label for cell in overview.heatmap}
    assert heatmap_labels == {"Funding", "Government", "Resource", "Partnership"}


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
    assert match.score >= 60
    # expanded category keywords (from the opportunity's focus areas) surface as factors
    assert any(
        any(area.split()[0] in factor for area in opportunity.focus_areas)
        for factor in match.match_factors
    )


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
    assert "Open Matching" in content
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
    assert reverse("project-pipeline", kwargs={"pk": project.pk}) in content
