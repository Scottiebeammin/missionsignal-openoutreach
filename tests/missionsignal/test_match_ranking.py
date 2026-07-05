"""Match ranking quality: deterministic tiebreakers within a score band,
term-count-weighted topical scoring, and the capped research-marker downrank.

The headline 0-100 score semantics are unchanged; ranking within a tie band is
driven by OpportunityMatch.sort_key (score, weighted focus-term hits, geography
granularity city > county > state > national, verification status
verified > reviewed > unverified, name).
"""
import dataclasses

import pytest

from openoutreach.core.models import Organization, Project
from openoutreach.funding.models import Funder, Opportunity
from openoutreach.signals.matching import (
    RESEARCH_PENALTY_CAP,
    RESEARCH_PENALTY_REASON,
    OpportunityMatch,
    _sort_matches,
    build_opportunity_matches,
    score_inventory_opportunity,
)

NONPROFIT_TYPES = [
    {"id": "12", "description": "Nonprofits having a 501(c)(3) status with the IRS"},
]


@pytest.fixture
def florida_project(db):
    organization = Organization.objects.create(
        name="Bright Harbor Youth Alliance",
        website="https://example.org",
        mission="Youth development and workforce readiness in Central Florida.",
        organization_type="nonprofit",
        city="Orlando",
        county="Orange County",
        state="Florida",
        service_area_notes="Central Florida",
        focus_areas=["Workforce Development", "Youth Opportunity"],
        beneficiaries=["youth"],
    )
    return Project.objects.create(
        organization=organization,
        name="Core Programs",
        programs="After-school mentoring, workforce development, and career readiness for youth.",
    )


def _match(name, **overrides) -> OpportunityMatch:
    base = OpportunityMatch(
        name=name,
        score=100,
        level="Excellent Match",
        opportunity_type="Grant",
        category="Funding Matches",
        reasons=[],
        match_factors=[],
        missing_factors=[],
        improvement_suggestions=[],
        potential_score=100,
        geography_relevance=30,
        suggested_lifecycle_stage="Discovered",
        current_lifecycle_status="Not in pipeline",
        owner_label="Unassigned",
        suggested_next_action="Review eligibility",
    )
    return dataclasses.replace(base, **overrides)


def _opportunity(project, **overrides) -> Opportunity:
    defaults = dict(
        project=project,
        name="Youth Workforce Development Grant",
        opportunity_type=Opportunity.OpportunityType.GRANT,
        source_type=Opportunity.SourceType.GOVERNMENT,
        geography=["National"],
        applicant_types=NONPROFIT_TYPES,
    )
    defaults.update(overrides)
    return Opportunity.objects.create(**defaults)


# --- Tiebreaker ordering ------------------------------------------------------

def test_tied_score_orders_by_focus_term_hits():
    weak = _match("Aaa Fund", focus_term_hits=1)
    strong = _match("Zzz Fund", focus_term_hits=8)
    assert _sort_matches([weak, strong]) == [strong, weak]


def test_tied_score_and_hits_orders_by_geography_granularity():
    national = _match("Aaa Fund", focus_term_hits=4, geography_granularity=1)
    state = _match("Mmm Fund", focus_term_hits=4, geography_granularity=2)
    city = _match("Zzz Fund", focus_term_hits=4, geography_granularity=4)
    assert _sort_matches([national, city, state]) == [city, state, national]


def test_tied_everything_orders_by_verification_then_name():
    unverified = _match("Aaa Fund", verification_rank=0)
    verified = _match("Zzz Fund", verification_rank=2)
    reviewed = _match("Mmm Fund", verification_rank=1)
    assert _sort_matches([unverified, verified, reviewed]) == [verified, reviewed, unverified]
    # Full tie: name is the deterministic final key.
    a, b = _match("Alpha Fund"), _match("Beta Fund")
    assert _sort_matches([b, a]) == [a, b]


def test_tied_funders_rank_better_first_not_alphabetical(florida_project):
    Funder.objects.create(
        name="Aaa Generic Fund",
        funder_type=Funder.FunderType.OTHER,
        geography=["National"],
        focus_areas=["Youth Development"],
        beneficiaries=["youth"],
        notes="Youth programs nationwide.",
    )
    Funder.objects.create(
        name="Zzz Orlando Workforce Fund",
        funder_type=Funder.FunderType.WORKFORCE_BOARD,
        geography=["Orlando", "Florida"],
        focus_areas=["Workforce Development", "Youth Development"],
        beneficiaries=["youth", "job seekers"],
        notes="Workforce development and career readiness grants for Orlando youth.",
        verification_status=Funder.VerificationStatus.VERIFIED,
    )
    overview = build_opportunity_matches(florida_project)
    funding = next(c for c in overview.categories if c.label == "Funding Matches")
    names = [m.name for m in funding.matches]
    assert names.index("Zzz Orlando Workforce Fund") < names.index("Aaa Generic Fund")


def test_sort_is_deterministic(florida_project):
    matches = [
        _match("B", focus_term_hits=2, geography_granularity=2),
        _match("A", focus_term_hits=2, geography_granularity=2),
        _match("C", focus_term_hits=5),
    ]
    assert _sort_matches(matches) == _sort_matches(list(reversed(matches)))


# --- Term-count weighted topical scoring --------------------------------------

def test_multiword_phrase_overlap_beats_single_generic_term(florida_project):
    on_topic = _opportunity(
        florida_project,
        name="Workforce Development Training Grant",
        eligibility_notes="Supports workforce development and career readiness programs for youth job seekers.",
    )
    generic = _opportunity(
        florida_project,
        name="Science Program for Youth",
        eligibility_notes="A science enrichment program that serves youth.",
    )
    on_topic_match = score_inventory_opportunity(florida_project, on_topic)
    generic_match = score_inventory_opportunity(florida_project, generic)
    assert on_topic_match.focus_term_hits > generic_match.focus_term_hits
    assert on_topic_match.score > generic_match.score


def test_focus_term_hits_count_real_occurrences_not_binary(florida_project):
    repeated = _opportunity(
        florida_project,
        name="Workforce Development Grant",
        eligibility_notes="Workforce development projects that expand workforce development capacity.",
    )
    single = _opportunity(
        florida_project,
        name="Community Grant",
        eligibility_notes="Includes a workforce development component.",
    )
    assert (
        score_inventory_opportunity(florida_project, repeated).focus_term_hits
        > score_inventory_opportunity(florida_project, single).focus_term_hits
    )


# --- Research-marker penalty ---------------------------------------------------

def test_research_marker_penalty_applied_capped_with_reason(florida_project):
    biomedical = _opportunity(
        florida_project,
        name="Youth Enjoy Science Research Education Program (R25 Clinical Trial Not Allowed)",
        eligibility_notes="Biomedical research education with laboratory experiences and postdoctoral mentors.",
    )
    match = score_inventory_opportunity(florida_project, biomedical)
    assert match.research_penalty == RESEARCH_PENALTY_CAP
    assert any(RESEARCH_PENALTY_REASON in reason for reason in match.reasons)
    assert not match.excluded

    plain = _opportunity(
        florida_project,
        name="Youth Enjoy Science Program",
        eligibility_notes="",
    )
    assert match.score < score_inventory_opportunity(florida_project, plain).score


def test_research_penalty_never_excludes_even_at_zero_score(florida_project):
    opportunity = _opportunity(
        florida_project,
        name="Dissertation Fellowship (R01)",
        geography=[],
        eligibility_notes="Predoctoral dissertation research; clinical trial; laboratory work.",
    )
    match = score_inventory_opportunity(florida_project, opportunity)
    assert not match.excluded
    assert match.score >= 0
    assert match.research_penalty == RESEARCH_PENALTY_CAP


def test_research_org_is_not_penalized(db):
    organization = Organization.objects.create(
        name="Orlando Research Institute",
        website="https://example.org",
        mission="Biomedical research education.",
        organization_type="research university",
        city="Orlando",
        county="Orange County",
        state="Florida",
        focus_areas=["Education"],
    )
    project = Project.objects.create(organization=organization, name="Research Programs")
    opportunity = _opportunity(
        project,
        name="Research Education Program (R25)",
        eligibility_notes="Laboratory research education.",
    )
    match = score_inventory_opportunity(project, opportunity)
    assert match.research_penalty == 0


# --- Two-tier funder pool (990-PF derived prefilter + cap) ---------------------

def test_derived_funder_pool_prefilters_and_caps(db):
    from openoutreach.signals.matching import DERIVED_FUNDER_SCORING_CAP, funder_matching_pool

    curated_off_topic = Funder.objects.create(
        name="Curated Opera Trust",
        funder_type=Funder.FunderType.OTHER,
        focus_areas=["Opera"],
        geography=["Vermont"],
    )
    # More on-focus derived foundations than the per-request scoring cap.
    Funder.objects.bulk_create([
        Funder(
            name=f"Derived Youth Foundation {i:04d}",
            funder_type=Funder.FunderType.FAMILY_FOUNDATION,
            focus_areas=["Youth Development"],
            is_derived=True,
            grant_count=i,
            grants_total_amount=1_000 * i,
        )
        for i in range(DERIVED_FUNDER_SCORING_CAP + 5)
    ])
    # A derived funder with no focus overlap is prefiltered out entirely,
    # no matter how large its giving history.
    Funder.objects.create(
        name="Derived Maritime Museum Fund",
        funder_type=Funder.FunderType.FAMILY_FOUNDATION,
        focus_areas=["Maritime History"],
        is_derived=True,
        grant_count=10_000,
    )

    pool = funder_matching_pool(["Youth Development"])
    names = {funder.name for funder in pool}
    derived_in_pool = [funder for funder in pool if funder.is_derived]

    assert curated_off_topic.name in names               # Tier A: always scored
    assert "Derived Maritime Museum Fund" not in names   # focus prefilter
    assert len(derived_in_pool) == DERIVED_FUNDER_SCORING_CAP
    # Largest givers first: only the smallest grant_count rows fell off the cap.
    assert min(funder.grant_count for funder in derived_in_pool) == 5
    assert max(funder.grant_count for funder in derived_in_pool) == DERIVED_FUNDER_SCORING_CAP + 4


def test_non_derived_funders_always_scored_in_matches(florida_project):
    Funder.objects.create(
        name="Curated Opera Trust",
        funder_type=Funder.FunderType.OTHER,
        focus_areas=["Opera"],       # zero overlap with the org's focus terms
        geography=["Vermont"],
    )
    Funder.objects.create(
        name="Derived Maritime Museum Fund",
        funder_type=Funder.FunderType.FAMILY_FOUNDATION,
        focus_areas=["Maritime History"],
        is_derived=True,
        grant_count=10_000,
    )
    overview = build_opportunity_matches(florida_project)
    funding = next(c for c in overview.categories if c.label == "Funding Matches")
    names = {match.name for match in funding.matches}
    assert "Curated Opera Trust" in names          # curated: scored regardless of focus
    assert "Derived Maritime Museum Fund" not in names  # derived + off-focus: not scored


def test_on_focus_derived_funders_are_scored(florida_project):
    # Focus areas overlap the org's "Workforce Development" focus term.
    Funder.objects.create(
        name="Derived Sunshine Youth Foundation",
        funder_type=Funder.FunderType.FAMILY_FOUNDATION,
        focus_areas=["Workforce Development"],
        geography=["Florida", "Orlando"],
        is_derived=True,
        grant_count=42,
    )
    overview = build_opportunity_matches(florida_project)
    funding = next(c for c in overview.categories if c.label == "Funding Matches")
    assert "Derived Sunshine Youth Foundation" in {match.name for match in funding.matches}
