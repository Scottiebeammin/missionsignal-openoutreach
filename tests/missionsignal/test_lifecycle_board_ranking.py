"""The lifecycle board came back in plain deadline order, so an Orlando
after-school STEM nonprofit opened its pipeline to embassy grants for Algeria,
Abu Dhabi and Myanmar — they simply had the nearest deadlines. The recommendation
views already knew those were unusable; the board never asked.
"""
from datetime import date, timedelta

import pytest

from openoutreach.core.models import Organization, Project
from openoutreach.funding.models import Opportunity
from openoutreach.signals.lifecycle import build_lifecycle_summary, rank_for_client

pytestmark = pytest.mark.django_db


def _project():
    org = Organization.objects.create(
        name="Tech Sassy Girlz", website="https://techsassygirlz.org",
        mission="STEM for girls in grades 6-12",
        state="Florida", city="Orlando",
        focus_areas=["STEM education", "girls empowerment", "youth development"],
        beneficiaries=["girls", "youth"],
    )
    return Project.objects.create(organization=org, name="TSG", programs="Code · Treks")


def _opp(project, name, days_out, **kw):
    return Opportunity.objects.create(
        project=project, name=name, deadline=date.today() + timedelta(days=days_out),
        opportunity_type=Opportunity.OpportunityType.GRANT,
        lifecycle_status=Opportunity.LifecycleStatus.DISCOVERED, **kw,
    )


def test_overseas_programs_are_dropped_not_merely_ranked_low():
    """A US-domestic nonprofit cannot use an embassy grant. That is a different
    statement from "weak match" and belongs off the board.

    Detection keys off the issuing agency, not the city in the title — these are
    State Department posts and Grants.gov files them under "U.S. Mission to X",
    which is why "Abu Dhabi" and "Yangon" being cities rather than countries
    never mattered.
    """
    p = _project()
    _opp(p, "Freedom250 Advancing U.S. AI Leadership in Algeria", 2,
         source_name="U.S. Mission to Algeria")
    _opp(p, "American Center Yangon Small Grants Competition", 3,
         source_name="U.S. Mission to Burma")
    keep, dropped = rank_for_client(list(Opportunity.objects.all()), p)
    assert dropped == 2
    assert keep == []


def test_an_eligible_match_outranks_a_nearer_junk_deadline():
    """The exact failure Marcus saw: nearest deadline won regardless of fit."""
    p = _project()
    _opp(p, "Freedom 250 Great American State Fair Initiative – Abu Dhabi", 1,
         source_name="U.S. Mission to the United Arab Emirates")
    good = _opp(p, "STEM Education for Girls Youth Program", 200,
                source_name="U.S. Department of Education")
    keep, _ = rank_for_client(list(Opportunity.objects.all()), p)
    assert [o.name for o in keep] == [good.name]


def test_ties_on_fit_still_fall_back_to_deadline():
    p = _project()
    later = _opp(p, "STEM Youth Program Beta", 90)
    sooner = _opp(p, "STEM Youth Program Alpha", 10)
    keep, _ = rank_for_client(list(Opportunity.objects.all()), p)
    assert [o.pk for o in keep] == [sooner.pk, later.pk]


def test_summary_reports_what_it_filtered():
    """Silently showing a smaller number than the client was told is its own
    problem — the count has to come back so the page can say so."""
    p = _project()
    _opp(p, "American Center Yangon Small Grants", 5, source_name="U.S. Mission to Burma")
    _opp(p, "STEM Girls Youth Mentorship", 40)
    summary = build_lifecycle_summary(project=p)
    assert summary.not_applicable == 1
    discovered = next(s for s in summary.stages if s.value == Opportunity.LifecycleStatus.DISCOVERED)
    assert discovered.count == 1
    assert [o.name for o in discovered.opportunities] == ["STEM Girls Youth Mentorship"]


def test_archived_rows_are_still_excluded():
    """Pre-existing guarantee — archiving is an operator retraction and must
    survive the new ordering."""
    p = _project()
    _opp(p, "STEM Girls Retracted Grant", 30, status=Opportunity.Status.ARCHIVED)
    summary = build_lifecycle_summary(project=p)
    assert all(not stage.opportunities for stage in summary.stages)


def test_operator_view_across_projects_keeps_deadline_order():
    """build_lifecycle_summary(project=None) spans every project and has no single
    organization to score against — it must not blow up or silently filter."""
    p = _project()
    _opp(p, "Freedom250 Algeria", 1, source_name="U.S. Mission to Algeria")
    _opp(p, "STEM Girls Youth", 60)
    summary = build_lifecycle_summary(project=None)
    assert summary.not_applicable == 0
    discovered = next(s for s in summary.stages if s.value == Opportunity.LifecycleStatus.DISCOVERED)
    assert discovered.count == 2


# --------------------------------------------------------------------------
# The board renders discovery.lifecycle_stages, which is built by a SEPARATE
# matcher (score_inventory_opportunity). Fixing build_lifecycle_summary alone
# left CREST sitting at the top of the live board with "Match 85" — the two
# systems disagreed about the same row. These pin them together.
# --------------------------------------------------------------------------

def test_discovery_board_drops_what_a_us_nonprofit_cannot_apply_for():
    from openoutreach.signals.discovery import build_discovery_overview

    p = _project()
    _opp(p, "American Center Yangon Small Grants", 5, source_name="U.S. Mission to Burma")
    _opp(p, "STEM Girls Youth Mentorship", 40, source_name="U.S. Department of Education")
    overview = build_discovery_overview(p)
    names = [i.opportunity.name for s in overview.lifecycle_stages for i in s.opportunities]
    assert names == ["STEM Girls Youth Mentorship"]


def test_discovery_board_sinks_university_only_programs():
    """CREST was row 1 on the live board at Match 85 while the recommendation
    views had it disqualified."""
    from openoutreach.signals.discovery import build_discovery_overview

    p = _project()
    _opp(p, "Centers of Research Excellence in Science and Technology", 120,
         source_name="U.S. National Science Foundation",
         eligibility_notes="*Who May Submit Proposals: Eligible institutions are MSIs that "
                           "offer graduate degrees in NSF STEM areas.")
    _opp(p, "STEM Girls Youth Program", 200, source_name="U.S. Department of Education")
    overview = build_discovery_overview(p)
    names = [i.opportunity.name for s in overview.lifecycle_stages for i in s.opportunities]
    assert names[0] == "STEM Girls Youth Program", names


def test_board_and_summary_agree_on_the_same_project():
    """The metric row and the board columns are built by different code paths and
    were showing different numbers (115 vs 203) for one project."""
    from openoutreach.signals.discovery import build_discovery_overview

    p = _project()
    _opp(p, "Freedom250 Algeria", 3, source_name="U.S. Mission to Algeria")
    _opp(p, "STEM Girls Youth A", 30, source_name="U.S. Department of Education")
    _opp(p, "STEM Girls Youth B", 60, source_name="U.S. Department of Education")
    overview = build_discovery_overview(p)
    board = sum(len(s.opportunities) for s in overview.lifecycle_stages)
    summary = sum(s.count for s in overview.lifecycle_summary.stages)
    assert board == summary == 2


def test_the_hidden_count_closes_against_the_board():
    """The banner number must equal what this board actually dropped. Sourcing it
    from the lifecycle summary reported 101 hidden over a board of 107 out of 216
    — three numbers on one screen that didn't reconcile."""
    from openoutreach.signals.discovery import build_discovery_overview

    p = _project()
    _opp(p, "Freedom250 Algeria", 3, source_name="U.S. Mission to Algeria")
    _opp(p, "American Center Yangon", 4, source_name="U.S. Mission to Burma")
    _opp(p, "STEM Girls Youth A", 30, source_name="U.S. Department of Education")
    overview = build_discovery_overview(p)
    shown = sum(len(s.opportunities) for s in overview.lifecycle_stages)
    assert shown + overview.not_applicable == overview.total_opportunities
