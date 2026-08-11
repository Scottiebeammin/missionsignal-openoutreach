"""State & Local section — local money grouped by the government that issues it.

The section exists because ranking local sources against federal notices by
keyword overlap does not work: a relevance floor was tried twice and shipped
invisible both times, since any floor is calibrated against one organization's
score histogram. These tests care most about the cases that AREN'T Tech Sassy
Girlz — an org in an uncovered state, an org with no geography, an org that has
sources but has never been ingested.
"""
import pytest

from openoutreach.core.models import Organization, Project
from openoutreach.funding.models import Opportunity
from openoutreach.signals.local_money import build_local_overview

pytestmark = pytest.mark.django_db


def _org(**kw):
    defaults = dict(
        name="Test Org", website="https://example.org", mission="Test mission",
        state="Florida", county="Orange", city="Orlando",
    )
    defaults.update(kw)
    org = Organization.objects.create(**defaults)
    return org, Project.objects.create(organization=org, name="Test", programs="Programs")


def _local_row(project, name, url, **kw):
    return Opportunity.objects.create(
        project=project, name=name,
        external_id=f"localgov:{abs(hash(name)) % 10**12}",
        source_urls=[url],
        opportunity_type=Opportunity.OpportunityType.GRANT,
        source_type=Opportunity.SourceType.GOVERNMENT,
        **kw,
    )


ORANGE_CCC = "https://www.orangecountyfl.net/familieshealthsocialsvcs/CitizensCommissionforChildren/grantfunding.aspx"


# ---------------------------------------------------------------- generalisation

def test_org_with_no_state_is_told_to_set_its_geography():
    """Not "no results" — the client can fix this one themselves."""
    _, project = _org(state="", county="", city="")
    overview = build_local_overview(project)
    assert overview.empty_reason == "no_geography"
    assert overview.has_state is False


def test_org_in_an_uncovered_state_is_told_the_gap_is_ours():
    """A Georgia nonprofit must not be shown the same message as a Florida one
    that simply hasn't been ingested — nothing they do fixes this."""
    _, project = _org(state="Georgia", county="Fulton", city="Atlanta")
    overview = build_local_overview(project)
    assert overview.empty_reason == "no_sources_registered"
    assert overview.source_total == 0
    assert overview.state_label == "Georgia"


def test_org_with_sources_but_no_ingest_is_distinguished_from_both():
    _, project = _org()
    overview = build_local_overview(project)
    assert overview.source_total > 0
    assert overview.opportunity_total == 0
    assert overview.empty_reason == "not_yet_ingested"


def test_a_populated_board_has_no_empty_reason():
    _, project = _org()
    _local_row(project, "Citizens' Commission for Children — Grant Funding", ORANGE_CCC)
    overview = build_local_overview(project)
    assert overview.empty_reason == ""
    assert overview.opportunity_total == 1


# ---------------------------------------------------------------- grouping

def test_jurisdictions_run_broadest_first():
    """State money is usually the largest award and the longest lead time, so a
    client reading top-down should meet it first."""
    _, project = _org()
    levels = [j.level for j in build_local_overview(project).jurisdictions]
    assert levels == sorted(levels, key=lambda l: {"state": 0, "county": 1, "city": 2}[l])


def test_county_label_does_not_stutter():
    _, project = _org(county="Orange")
    labels = [j.label for j in build_local_overview(project).jurisdictions]
    assert "Orange County" in labels
    assert "Orange County County" not in labels


def test_county_already_containing_the_word_is_left_alone():
    _, project = _org(county="Miami-Dade County")
    labels = [j.label for j in build_local_overview(project).jurisdictions]
    assert not any(l.endswith("County County") for l in labels)


def test_rows_attach_to_their_source_by_url_not_name():
    """The join is source_urls, so a source can be renamed without orphaning
    everything ingested from it."""
    _, project = _org()
    _local_row(project, "Some Program", ORANGE_CCC)
    overview = build_local_overview(project)
    matched = [g for j in overview.jurisdictions for g in j.groups if g.count]
    assert len(matched) == 1
    assert matched[0].source.url == ORANGE_CCC


def test_a_source_with_no_rows_still_appears():
    """A matched-but-unfetched funder is information, not absence."""
    _, project = _org()
    _local_row(project, "Some Program", ORANGE_CCC)
    overview = build_local_overview(project)
    empty = [g for j in overview.jurisdictions for g in j.groups if not g.count and not g.is_blocked]
    assert empty, "sources without ingested rows should still be listed"


# ---------------------------------------------------------------- honesty

def test_blocked_sources_are_surfaced_not_hidden():
    """A source we know exists and can't reach is a stated gap, not silence."""
    _, project = _org()
    overview = build_local_overview(project)
    blocked = [g for j in overview.jurisdictions for g in j.blocked_groups]
    for group in blocked:
        assert group.source.blocked, "a blocked source must explain why"


def test_blocked_sources_never_head_a_jurisdiction_with_real_money_in_it():
    _, project = _org()
    _local_row(project, "Some Program", ORANGE_CCC)
    for jurisdiction in build_local_overview(project).jurisdictions:
        flags = [g.is_blocked for g in jurisdiction.groups]
        assert flags == sorted(flags), "blocked sources sort last"


def test_missing_county_and_city_are_reported_because_they_cost_sources():
    """An org that never set its county silently loses every county-level funder,
    and nothing on the page would otherwise say so."""
    _, project = _org(county="", city="")
    overview = build_local_overview(project)
    assert overview.missing_geography == ["county", "city"]


def test_full_geography_reports_nothing_missing():
    _, project = _org()
    assert build_local_overview(project).missing_geography == []


def test_expired_and_archived_rows_stay_off_the_section():
    _, project = _org()
    _local_row(project, "Live Program", ORANGE_CCC)
    _local_row(project, "Dead Program", ORANGE_CCC, status=Opportunity.Status.EXPIRED)
    _local_row(project, "Pulled Program", ORANGE_CCC, status=Opportunity.Status.ARCHIVED)
    assert build_local_overview(project).opportunity_total == 1


def test_another_projects_local_rows_do_not_leak_in():
    _, project = _org()
    _, other = _org(name="Other Org")
    _local_row(other, "Their Program", ORANGE_CCC)
    assert build_local_overview(project).opportunity_total == 0


# ---------------------------------------------------------------- the page itself

@pytest.fixture
def staff_client(client, django_user_model):
    user = django_user_model.objects.create_user(
        username="operator", password="x", is_staff=True,
    )
    client.force_login(user)
    return client


def test_the_section_renders_on_the_board(staff_client):
    """Every defect in this area shipped green. The unit tests above all passed
    while the board was wrong, so the template has to be exercised too."""
    _, project = _org()
    _local_row(project, "Citizens' Commission for Children — Grant Funding", ORANGE_CCC)
    response = staff_client.get(f"/projects/{project.pk}/opportunities/")
    assert response.status_code == 200
    body = response.content.decode()
    assert "State &amp; Local Funding" in body
    assert "Citizens&#x27; Commission for Children — Grant Funding" in body or \
           "Citizens' Commission for Children — Grant Funding" in body


@pytest.mark.parametrize("kw,expected", [
    ({"state": "", "county": "", "city": ""}, "know where you operate"),
    ({"state": "Georgia", "county": "Fulton", "city": "Atlanta"}, "sources registered yet"),
    ({}, "none fetched yet"),
])
def test_each_empty_state_renders_its_own_message(staff_client, kw, expected):
    """Three different people have to act on these three cases; one shared
    "nothing here" would hide two of them."""
    _, project = _org(**kw)
    body = staff_client.get(f"/projects/{project.pk}/opportunities/").content.decode()
    assert expected in body


def test_a_page_level_row_does_not_print_its_own_name_twice(staff_client):
    """Without an LLM key the row IS the source page, so name == source name."""
    _, project = _org()
    name = "Orange County Citizens' Commission for Children — Grant Funding"
    _local_row(project, name, ORANGE_CCC)
    body = staff_client.get(f"/projects/{project.pk}/opportunities/").content.decode()
    section = body[body.index("State &amp; Local Funding"):body.index("Top 10 Recommended")]
    assert section.count(name.replace("'", "&#x27;")) + section.count(name) == 1


def test_a_program_level_row_keeps_its_source_attribution(staff_client):
    """When the names differ the attribution earns its line back."""
    _, project = _org()
    _local_row(project, "Youth Mental Health Mini-Grant", ORANGE_CCC)
    body = staff_client.get(f"/projects/{project.pk}/opportunities/").content.decode()
    assert "Youth Mental Health Mini-Grant" in body
    assert "Citizens" in body  # the source name is still shown alongside it


def test_local_rows_are_not_also_ranked_against_federal_ones(staff_client):
    """The whole point of the section: local money stops competing in a ranking
    it structurally loses. It must not appear in both places."""
    _, project = _org()
    _local_row(project, "Citizens' Commission for Children — Grant Funding", ORANGE_CCC)
    response = staff_client.get(f"/projects/{project.pk}/opportunities/")
    assert all(
        not o.external_id.startswith("localgov:")
        for o in response.context["all_opportunities"]
    )
    assert response.context["local_overview"].opportunity_total == 1
