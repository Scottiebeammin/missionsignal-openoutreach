"""'Not a fit' feedback loop: toggle endpoint + view-layer suppression.

Suppression is view-local (matching.py stays a pure scorer): the opportunities
workspace drops flagged opportunities from the top-10 shelf (they stay in the
full list with a not_a_fit flag), and the match dashboard drops flagged
reference matches (funder/government/resource/partner, keyed by record name)
from MatchOverview.top_recommended.
"""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from openoutreach.funding.models import Funder, Opportunity
from openoutreach.signals.demo import seed_missionsignal_demo
from openoutreach.signals.models import MatchFeedback

pytestmark = pytest.mark.django_db

NONPROFIT_TYPES = [
    {"id": "12", "description": "Nonprofits having a 501(c)(3) status with the IRS"},
]


@pytest.fixture
def feedback_project(db):
    user, _organization, project = seed_missionsignal_demo()
    return project, user


@pytest.fixture
def workspace_opportunities(feedback_project):
    project, _user = feedback_project
    first = Opportunity.objects.create(
        project=project,
        name="Youth Workforce Development Grant",
        opportunity_type=Opportunity.OpportunityType.GRANT,
        source_type=Opportunity.SourceType.GOVERNMENT,
        geography=["National"],
        applicant_types=NONPROFIT_TYPES,
    )
    second = Opportunity.objects.create(
        project=project,
        name="Career Readiness Technology Fund",
        opportunity_type=Opportunity.OpportunityType.GRANT,
        source_type=Opportunity.SourceType.GOVERNMENT,
        geography=["National"],
        applicant_types=NONPROFIT_TYPES,
    )
    return first, second


@pytest.fixture
def matching_funder(feedback_project):
    """A real-domain funder aligned with the demo org so it lands in top_recommended."""
    return Funder.objects.create(
        name="Lakeshore Youth Opportunity Fund",
        website="https://lakeshoreyouthfund.org",
        geography=["Orlando", "Orange", "Florida"],
        focus_areas=["Workforce Development", "Youth Development", "Career Readiness"],
        beneficiaries=["Youth"],
        active=True,
    )


def _post_feedback(client, project, kind, target_key, next_url=""):
    return client.post(
        reverse("project-match-feedback", kwargs={"pk": project.pk}),
        {"kind": kind, "target_key": target_key, "next": next_url},
    )


# --- endpoint: create / toggle / gate -------------------------------------------------


def test_feedback_post_creates_row(client, feedback_project):
    project, user = feedback_project
    client.force_login(user)

    response = _post_feedback(client, project, "opportunity", "123")

    assert response.status_code == 302
    row = MatchFeedback.objects.get(project=project, kind="opportunity", target_key="123")
    assert row.verdict == MatchFeedback.Verdict.NOT_A_FIT
    assert row.created_by == user


def test_feedback_post_twice_toggles_off(client, feedback_project):
    project, user = feedback_project
    client.force_login(user)

    _post_feedback(client, project, "funder", "Some Foundation")
    assert MatchFeedback.objects.filter(project=project).count() == 1

    _post_feedback(client, project, "funder", "Some Foundation")
    assert MatchFeedback.objects.filter(project=project).count() == 0


def test_feedback_preserves_next_redirect(client, feedback_project):
    project, user = feedback_project
    client.force_login(user)
    next_url = f"/projects/{project.pk}/matches/?all=1"

    response = _post_feedback(client, project, "funder", "Some Foundation", next_url=next_url)

    assert response.status_code == 302
    assert response["Location"] == next_url


def test_feedback_rejects_unknown_kind(client, feedback_project):
    project, user = feedback_project
    client.force_login(user)

    _post_feedback(client, project, "spaceship", "X")

    assert MatchFeedback.objects.count() == 0


def test_non_member_cannot_post_feedback(client, feedback_project):
    project, _user = feedback_project
    outsider = get_user_model().objects.create_user(
        username="feedback-outsider", password="password",
    )
    client.force_login(outsider)

    response = _post_feedback(client, project, "opportunity", "123")

    assert response.status_code == 404
    assert MatchFeedback.objects.count() == 0


# --- suppression: opportunities workspace ---------------------------------------------


def test_flagged_opportunity_leaves_top_ten(client, feedback_project, workspace_opportunities):
    # The demo seed plus the fixture pair gives a pool larger than the shelf, so
    # flag whatever currently leads the shelf and assert the next-best refills.
    project, user = feedback_project
    client.force_login(user)
    url = reverse("project-opportunities", kwargs={"pk": project.pk})

    before = client.get(url)
    top_before = [o.pk for o in before.context["top_opportunities"]]
    flagged_pk, runner_up_pk = top_before[0], top_before[1]

    MatchFeedback.objects.create(project=project, kind="opportunity", target_key=str(flagged_pk))
    after = client.get(url)

    top_pks = [o.pk for o in after.context["top_opportunities"]]
    assert flagged_pk not in top_pks
    assert runner_up_pk in top_pks
    # The shelf refills back to full size from the remaining pool.
    assert len(top_pks) == len(top_before)
    # Still browsable in the full list, tagged not_a_fit.
    all_by_pk = {o.pk: o for o in after.context["all_opportunities"]}
    assert all_by_pk[flagged_pk].not_a_fit is True
    assert all_by_pk[runner_up_pk].not_a_fit is False


def test_workspace_renders_not_a_fit_button(client, feedback_project, workspace_opportunities):
    project, user = feedback_project
    client.force_login(user)

    response = client.get(reverse("project-opportunities", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert "Not a fit" in content
    assert reverse("project-match-feedback", kwargs={"pk": project.pk}) in content


# --- suppression: match dashboard top_recommended -------------------------------------


def test_flagged_funder_leaves_top_recommended(client, feedback_project, matching_funder):
    project, user = feedback_project
    client.force_login(user)
    url = reverse("project-matches", kwargs={"pk": project.pk})

    before = client.get(url)
    assert matching_funder.name in [
        m.name for m in before.context["match_overview"].top_recommended
    ]

    MatchFeedback.objects.create(
        project=project, kind="funder", target_key=matching_funder.name,
    )
    after = client.get(url)

    overview = after.context["match_overview"]
    assert matching_funder.name not in [m.name for m in overview.top_recommended]
    assert matching_funder.name not in [
        m.name for m, _kind in after.context["top_recommended_cards"]
    ]
    # Category inventories stay complete — only the recommendation shelf is curated.
    funding = next(c for c in overview.categories if c.label == "Funding Matches")
    assert matching_funder.name in [m.name for m in funding.matches]


def test_match_dashboard_cards_carry_feedback_kind(client, feedback_project, matching_funder):
    project, user = feedback_project
    client.force_login(user)

    response = client.get(reverse("project-matches", kwargs={"pk": project.pk}))

    cards = dict(
        (m.name, kind) for m, kind in response.context["top_recommended_cards"]
    )
    assert cards[matching_funder.name] == "funder"
    content = response.content.decode()
    assert "Not a fit" in content
    assert reverse("project-match-feedback", kwargs={"pk": project.pk}) in content
