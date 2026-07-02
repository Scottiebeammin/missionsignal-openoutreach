"""Geography + applicant-type eligibility intelligence for Grants.gov opportunities.

Covers: national partial geography credit, home-state full credit, other-state
exclusion, nonprofit-eligibility exclusion, and ingestion field population
(geography / applicant_types / eligibility_notes) with the API mocked.
"""
import pytest

from openoutreach.core.models import Organization, Project
from openoutreach.funding import grants_gov
from openoutreach.funding.grants_gov import (
    detect_states,
    geography_for_hit,
    ingest_grants_for_project,
    normalize_applicant_types,
)
from openoutreach.funding.models import Opportunity
from openoutreach.signals.matching import (
    MATCH_WEIGHTS,
    NATIONAL_GEOGRAPHY_POINTS,
    applicant_types_allow_nonprofits,
    score_inventory_opportunity,
)

NONPROFIT_TYPES = [
    {"id": "12", "description": "Nonprofits having a 501(c)(3) status with the IRS, other than institutions of higher education"},
]
STATE_GOV_ONLY_TYPES = [{"id": "00", "description": "State governments"}]
INDIVIDUALS_ONLY_TYPES = [{"id": "21", "description": "Individuals"}]


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
        focus_areas=["Youth Opportunity"],
        beneficiaries=["youth"],
    )
    return Project.objects.create(
        organization=organization,
        name="Core Programs",
        programs="After-school mentoring and career readiness for youth.",
    )


def _opportunity(project, **overrides) -> Opportunity:
    defaults = dict(
        project=project,
        name="Youth Development Grant",
        opportunity_type=Opportunity.OpportunityType.GRANT,
        source_type=Opportunity.SourceType.GOVERNMENT,
        geography=["National"],
        applicant_types=NONPROFIT_TYPES,
    )
    defaults.update(overrides)
    return Opportunity.objects.create(**defaults)


# --- Geography scoring -------------------------------------------------------

def test_national_scope_gets_partial_geography_credit(florida_project):
    opportunity = _opportunity(florida_project, geography=["National"])
    match = score_inventory_opportunity(florida_project, opportunity)
    assert not match.excluded
    assert match.geography_relevance == NATIONAL_GEOGRAPHY_POINTS
    assert "National program — eligible in any state" in match.reasons


def test_home_state_scope_gets_full_geography_credit(florida_project):
    opportunity = _opportunity(florida_project, geography=["Florida"])
    match = score_inventory_opportunity(florida_project, opportunity)
    assert not match.excluded
    assert match.geography_relevance == MATCH_WEIGHTS["geography"]
    assert "Geography Alignment" in match.match_factors


def test_other_state_only_scope_is_excluded(florida_project):
    opportunity = _opportunity(florida_project, geography=["California"])
    match = score_inventory_opportunity(florida_project, opportunity)
    assert match.excluded
    assert match.score == 0
    assert "California" in match.exclusion_reason


def test_multi_state_scope_including_home_state_is_kept(florida_project):
    opportunity = _opportunity(florida_project, geography=["Georgia", "Florida"])
    match = score_inventory_opportunity(florida_project, opportunity)
    assert not match.excluded
    assert match.geography_relevance == MATCH_WEIGHTS["geography"]


def test_empty_geography_gets_no_credit_but_is_not_excluded(florida_project):
    opportunity = _opportunity(florida_project, geography=[])
    match = score_inventory_opportunity(florida_project, opportunity)
    assert not match.excluded
    assert match.geography_relevance == 0


# --- Eligibility screening ---------------------------------------------------

def test_state_governments_only_is_excluded(florida_project):
    opportunity = _opportunity(florida_project, applicant_types=STATE_GOV_ONLY_TYPES)
    match = score_inventory_opportunity(florida_project, opportunity)
    assert match.excluded
    assert "nonprofit" in match.exclusion_reason.casefold()


def test_individuals_only_is_excluded(florida_project):
    opportunity = _opportunity(florida_project, applicant_types=INDIVIDUALS_ONLY_TYPES)
    match = score_inventory_opportunity(florida_project, opportunity)
    assert match.excluded


def test_unknown_applicant_types_are_kept(florida_project):
    opportunity = _opportunity(florida_project, applicant_types=[])
    match = score_inventory_opportunity(florida_project, opportunity)
    assert not match.excluded


def test_nonprofit_eligible_opportunity_is_kept(florida_project):
    opportunity = _opportunity(florida_project, applicant_types=NONPROFIT_TYPES)
    match = score_inventory_opportunity(florida_project, opportunity)
    assert not match.excluded


def test_applicant_types_allow_nonprofits_tri_state():
    assert applicant_types_allow_nonprofits([]) is None
    assert applicant_types_allow_nonprofits(None) is None
    assert applicant_types_allow_nonprofits(NONPROFIT_TYPES) is True
    assert applicant_types_allow_nonprofits([{"id": "99", "description": "Unrestricted"}]) is True
    assert applicant_types_allow_nonprofits([{"id": "25", "description": "Others"}]) is True
    assert applicant_types_allow_nonprofits(STATE_GOV_ONLY_TYPES) is False
    assert applicant_types_allow_nonprofits(INDIVIDUALS_ONLY_TYPES) is False


# --- Ingestion helpers -------------------------------------------------------

def test_geography_for_hit_defaults_to_national():
    assert geography_for_hit("Youth Conservation Corps - Bureau wide") == ["National"]


def test_geography_for_hit_detects_state_in_title():
    assert geography_for_hit("FY26 Florida Coastal Resilience Program") == ["Florida"]
    assert detect_states("New Mexico and Texas border initiative") == ["New Mexico", "Texas"]


def test_normalize_applicant_types_handles_dicts_and_strings():
    raw = [{"id": "12", "description": "Nonprofits"}, "Unrestricted", {"id": "", "description": ""}]
    assert normalize_applicant_types(raw) == [
        {"id": "12", "description": "Nonprofits"},
        {"id": "", "description": "Unrestricted"},
    ]


# --- Ingestion field population (API mocked) ---------------------------------

def test_ingest_populates_geography_and_eligibility(florida_project, monkeypatch):
    hits = [
        {
            "id": "362787",
            "number": "L26AS00064",
            "title": "FY26 Youth Conservation Corps - Bureau wide",
            "agency": "Bureau of Land Management",
            "openDate": "06/12/2026",
            "closeDate": "10/16/2026",
        },
        {
            "id": "999001",
            "number": "FL-ONLY-1",
            "title": "Florida Youth Resilience Program",
            "agency": "Test Agency",
            "openDate": "06/01/2026",
            "closeDate": "12/01/2026",
        },
    ]
    details = {
        "362787": {
            "applicantTypes": [{"id": "00", "description": "State governments"}],
            "applicantEligibilityDesc": "Individuals and for-profit organizations are ineligible.",
        },
        "999001": {
            "applicantTypes": NONPROFIT_TYPES,
            "applicantEligibilityDesc": "",
        },
    }
    monkeypatch.setattr(grants_gov, "search_grants", lambda kw, rows=25: hits)
    monkeypatch.setattr(grants_gov, "fetch_opportunity_details", lambda gid: details[gid])

    result = ingest_grants_for_project(florida_project, keywords=["youth"])
    assert result["created"] == 2

    national = Opportunity.objects.get(external_id="grants.gov:362787")
    assert national.geography == ["National"]
    assert national.applicant_types == [{"id": "00", "description": "State governments"}]
    assert national.eligibility_notes.startswith("Individuals and for-profit")

    state_scoped = Opportunity.objects.get(external_id="grants.gov:999001")
    assert state_scoped.geography == ["Florida"]
    assert state_scoped.applicant_types == NONPROFIT_TYPES
