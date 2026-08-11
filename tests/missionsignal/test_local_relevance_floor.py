"""Local sources reach a project only by matching its geography. Scoring them on
keyword overlap — the federal test — put three of Tech Sassy Girlz's four county
and city sources at 0, below the `relevance > 0` cut, so the whole state/local
integration landed in the database and nowhere the client could see it.
"""
import pytest

from openoutreach.funding.relevance import (
    LOCAL_GEOGRAPHY_FLOOR,
    is_local_government_source,
    opportunity_relevance,
)


class FakeOpportunity:
    def __init__(self, name="", external_id="", notes="", eligibility_notes="",
                 source_name="", focus_areas=None, beneficiaries=None):
        self.name = name
        self.external_id = external_id
        self.notes = notes
        self.eligibility_notes = eligibility_notes
        self.source_name = source_name
        self.focus_areas = focus_areas or []
        self.beneficiaries = beneficiaries or []


KEYWORDS = {"stem", "girls", "youth", "mentorship", "workforce", "coding", "scholarships", "entrepreneurship"}

# The four real rows pull_local_grants saved for Tech Sassy Girlz (project 3).
LOCAL_ROWS = [
    "Orange County Citizens' Commission for Children — Grant Funding",
    "Orange County — Neighborhood Grants",
    "City of Orlando — Community Investment Program",
    "City of Orlando — For Non-Profits and Community Organizations",
]


@pytest.mark.parametrize("name", LOCAL_ROWS)
def test_every_real_local_row_clears_the_visibility_cut(name):
    """Regression: three of these four scored 0 on prod and never appeared."""
    opp = FakeOpportunity(name=name, external_id="localgov:abc123")
    assert opportunity_relevance(opp, KEYWORDS) >= LOCAL_GEOGRAPHY_FLOOR
    assert opportunity_relevance(opp, KEYWORDS) > 0


def test_federal_rows_are_not_floored():
    """The floor is earned by passing a geography match. A federal notice with no
    keyword overlap still scores 0 and stays off the recommendations."""
    opp = FakeOpportunity(name="Deep Sea Drilling Platform Safety", external_id="grants.gov:12345")
    assert opportunity_relevance(opp, KEYWORDS) == 0


def test_a_local_row_that_does_match_scores_above_the_floor():
    """The floor is a minimum, not a flat rate — real overlap still counts."""
    opp = FakeOpportunity(
        name="Orange County STEM Girls Youth Workforce Mentorship Coding Scholarships Fund",
        external_id="localgov:abc123",
    )
    assert opportunity_relevance(opp, KEYWORDS) > LOCAL_GEOGRAPHY_FLOOR


def test_floor_clears_the_marginal_federal_band():
    """The prod distribution has 8 federal rows at exactly 4 — coincidental keyword
    hits like "Medical Student Education". A floor level with that band leaves local
    rows tied, and since they carry no deadline they lose the tiebreak and fall off
    the shelf entirely. The floor has to clear it, not sit in it."""
    marginal_federal = 4
    assert LOCAL_GEOGRAPHY_FLOOR > marginal_federal


def test_floor_does_not_outrank_a_strong_federal_match():
    """A neighbourhood-projects fund must not displace a program that genuinely
    matches the mission — that would trade one bad ranking for another."""
    local = FakeOpportunity(name="Orange County — Neighborhood Grants", external_id="localgov:abc")
    federal = FakeOpportunity(
        name="STEM Girls Youth Mentorship Workforce Coding Scholarships Entrepreneurship Program",
        external_id="grants.gov:999",
    )
    assert opportunity_relevance(federal, KEYWORDS) > opportunity_relevance(local, KEYWORDS)


def test_floor_applies_even_with_no_org_keywords():
    """An unprofiled org has no keywords, so every federal row scores 0. The
    local rows are still geographically true and must survive."""
    local = FakeOpportunity(name="City of Orlando — Community Investment Program",
                            external_id="localgov:abc")
    federal = FakeOpportunity(name="Anything At All", external_id="grants.gov:1")
    assert opportunity_relevance(local, set()) == LOCAL_GEOGRAPHY_FLOOR
    assert opportunity_relevance(federal, set()) == 0


@pytest.mark.parametrize("external_id,expected", [
    ("localgov:9f8e7d", True),
    ("grants.gov:362839", False),
    ("funder:41", False),
    ("", False),
    (None, False),
])
def test_local_source_detection(external_id, expected):
    assert is_local_government_source(FakeOpportunity(external_id=external_id)) is expected
