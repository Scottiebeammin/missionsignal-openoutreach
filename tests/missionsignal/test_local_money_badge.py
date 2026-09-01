"""A verified local grant must show as verified to the client.

The State & Local section hardcoded the "⚠ Verify first" badge with no conditional, so
human verification was invisible on the one section where local money lives. An operator
could read a county's own page, confirm the programme and its deadline, mark the row
verified — and the client would still be told to go verify it.

Found 2026-09-01 while verifying two Orange County programmes against
orangecountyfl.net for the executive film: the rows came back is_confirmed=True and the
page still rendered zero verified badges.

The bar is the same one the rest of the product uses (Opportunity.is_confirmed):
human-verified AND backed by a real, non-placeholder source link. Both halves matter —
the tests below pin each one.
"""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from openoutreach.core.models import Organization, Project
from openoutreach.funding.models import Opportunity
from openoutreach.funding.relevance import LOCAL_SOURCE_PREFIX
from openoutreach.signals.local_money import sources_for_organization


@pytest.fixture
def local_board(db):
    user = get_user_model().objects.create_user(username="local-badge", password="password")
    organization = Organization.objects.create(
        name="Riverbend Girls Collective",
        website="https://riverbend.example",
        mission="Youth development and mentoring for girls ages 9 to 18.",
        city="Orlando",
        county="Orange",
        state="Florida",
        focus_areas=["youth development"],
    )
    project = Project.objects.create(
        organization=organization,
        name="Opportunity Web",
        programs="Youth development and after-school programming.",
    )
    project.users.add(user)
    return project, user


def _county_source_url(organization):
    """A REAL registered source URL for this org's county.

    The section indexes opportunities against the source registry by exact URL, so a
    made-up link renders nothing at all and the test passes or fails for the wrong
    reason. Ask the registry instead of hardcoding.
    """
    sources = sources_for_organization(organization, include_blocked=True)
    county = [s for s in sources if s.level == "county"]
    assert county, "no county source registered for this organization"
    return county[0].url


def _local(project, name, verified=False, url=None, **kw):
    """A row shaped like one pull_local_grants writes — keyed by the localgov: prefix."""
    return Opportunity.objects.create(
        project=project,
        name=name,
        opportunity_type=Opportunity.OpportunityType.GRANT,
        status=Opportunity.Status.ACTIVE,
        external_id=f"{LOCAL_SOURCE_PREFIX}{name.lower().replace(' ', '-')}",
        geography="Orange County, Florida",
        source_name="Orange County",
        verification_status="verified" if verified else "needs_review",
        source_urls=[url if url is not None else _county_source_url(project.organization)],
        **kw,
    )


def _render(client, project):
    return client.get(reverse("project-opportunities", kwargs={"pk": project.pk})).content.decode()


# The page also carries a LEGEND explaining both tiers ("<strong>✓ Verified</strong>
# means ..."), which is present no matter what. Matching the bare text would pass on the
# legend alone and prove nothing, so assert on the badge element itself: badges are
# <span>, the legend is <strong>.
VERIFIED_BADGE = ">✓ Verified</span>"
VERIFY_FIRST_BADGE = ">⚠ Verify first</span>"


@pytest.mark.django_db
def test_verified_local_grant_shows_the_verified_badge(client, local_board):
    project, user = local_board
    client.force_login(user)
    opp = _local(
        project,
        "Youth Sports Enhancement Grant",
        verified=True,
    )
    assert opp.is_confirmed is True

    content = _render(client, project)

    assert VERIFIED_BADGE in content, "a human-verified local grant still read as unverified"


@pytest.mark.django_db
def test_unverified_local_grant_still_says_verify_first(client, local_board):
    """Verify-first stays the default — the fix must not flip the whole section green."""
    project, user = local_board
    client.force_login(user)
    _local(
        project,
        "Sustainable Communities Grant",
    )

    content = _render(client, project)

    assert VERIFY_FIRST_BADGE in content
    assert VERIFIED_BADGE not in content


@pytest.mark.django_db
def test_a_row_with_no_registered_source_never_reaches_the_section(client, local_board):
    """Why the green badge cannot be faked here, and it is a property of the section.

    The section indexes opportunities against the source REGISTRY by exact URL, so a row
    pointing at anything unregistered — a placeholder, a guess — never gets a card there.
    Which means every row that does render a local card necessarily carries a real,
    registered https link, and Opportunity.is_confirmed collapses to just "has a human
    verified it".

    That is why the badge fix is safe: there is no path where a placeholder-sourced row
    earns a green badge. (The row may still be listed elsewhere on the page — this is
    about the local-money cards, so assert on the badge, not on the name.)
    """
    project, user = local_board
    client.force_login(user)
    _local(
        project,
        "Placeholder Sourced Grant",
        verified=True,
        url="https://funder.example.org/grants",
    )

    content = _render(client, project)

    assert VERIFIED_BADGE not in content
