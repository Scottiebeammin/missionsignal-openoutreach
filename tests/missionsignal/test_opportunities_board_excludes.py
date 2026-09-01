"""Disqualified opportunities leave the board entirely — they are not ranked last.

Before 2026-09-01 this view scored off-geography and research grants as relevance 0
and kept them, so they stayed in "see all" and inflated the "N total found" headline.
Measured on production that was roughly half of every client's board: 102 of 224 rows
for Empowered Girls, 112 of 229 for Tech Sassy Girlz, 102 of 199 for Women on the Rise.
A women's re-entry org was being shown 199 opportunities of which 41 were real.

The top-10 shelf also had a fallback — `[...relevant...] or [...ranked...]` — that
backfilled the shelf with disqualified rows whenever a client had no relevant matches,
which is the one case where it does the most damage. An empty shelf is now allowed and
is treated as a signal that the organization profile needs filling in.
"""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from openoutreach.core.models import Organization, Project
from openoutreach.funding.models import Opportunity


@pytest.fixture
def board(db):
    user = get_user_model().objects.create_user(
        username="board-member", password="password",
    )
    organization = Organization.objects.create(
        name="Riverbend Girls Collective",
        website="https://riverbend.example",
        mission="Youth development and mentoring for girls ages 9 to 18.",
        city="Orlando",
        county="Orange",
        state="Florida",
    )
    project = Project.objects.create(
        organization=organization,
        name="Opportunity Web",
        programs="Youth development, mentoring, and after-school programming for girls.",
    )
    project.users.add(user)
    return project, user


def _make(project, name, focus_areas=None, **kw):
    return Opportunity.objects.create(
        project=project,
        name=name,
        opportunity_type=Opportunity.OpportunityType.GRANT,
        status=Opportunity.Status.ACTIVE,
        # Default to the org's own focus so the row scores as a match; pass [] for a
        # row that should be eligible but irrelevant.
        focus_areas=["Youth Development"] if focus_areas is None else focus_areas,
        **kw,
    )


def _get(client, project):
    return client.get(reverse("project-opportunities", kwargs={"pk": project.pk}))


@pytest.mark.django_db
def test_off_geography_row_is_absent_from_the_board(client, board):
    project, user = board
    client.force_login(user)
    relevant = _make(project, "Youth Mentoring Program Grant", geography="Orange County, Florida")
    foreign = _make(project, "Support for Youth Journalists in Indonesia", geography="Indonesia")

    response = _get(client, project)
    all_pks = [o.pk for o in response.context["all_opportunities"]]

    assert relevant.pk in all_pks
    assert foreign.pk not in all_pks, "a disqualified row was still browsable in 'see all'"


@pytest.mark.django_db
def test_research_grant_is_absent_from_the_board(client, board):
    project, user = board
    client.force_login(user)
    relevant = _make(project, "Youth Mentoring Program Grant", geography="Orange County, Florida")
    research = _make(
        project,
        "DoW Kidney Cancer, Academy of Kidney Cancer Investigators - Early-Career Scholar Award",
        geography="United States",
    )

    response = _get(client, project)
    all_pks = [o.pk for o in response.context["all_opportunities"]]

    assert relevant.pk in all_pks
    assert research.pk not in all_pks


@pytest.mark.django_db
def test_headline_total_counts_only_what_the_client_can_apply_for(client, board):
    """`opportunity_total` drives 'N total found' and 'See all N' in the template."""
    project, user = board
    client.force_login(user)
    _make(project, "Youth Mentoring Program Grant", geography="Orange County, Florida")
    _make(project, "Support for Youth Journalists in Indonesia", geography="Indonesia")
    _make(project, "Youth Health Clinical Trial Program", geography="United States")

    response = _get(client, project)

    assert response.context["opportunity_total"] == 1


@pytest.mark.django_db
def test_no_relevant_matches_shows_an_empty_shelf_not_filler(client, board):
    """The removed `or` fallback: the shelf must stay empty rather than backfill."""
    project, user = board
    client.force_login(user)
    # Eligible but nothing to do with this organization — relevance 0, not disqualified.
    _make(project, "Rangeland Resource Management - Bureau Wide", focus_areas=[], geography="United States")

    response = _get(client, project)

    assert response.context["top_opportunities"] == []
    assert response.context["relevant_total"] == 0
    # The row is still browsable — it is eligible, just not a match.
    assert response.context["opportunity_total"] == 1


@pytest.mark.django_db
def test_empty_shelf_points_the_client_at_their_profile(client, board):
    project, user = board
    client.force_login(user)
    _make(project, "Rangeland Resource Management - Bureau Wide", focus_areas=[], geography="United States")

    content = _get(client, project).content.decode()

    assert "Nothing here matches your organization yet" in content
    assert reverse("project-organization", kwargs={"pk": project.pk}) in content
