"""The fetchOpportunity detail call we already make for applicantTypes also
carries the money fields. These lock in that we keep them, and that a bad or
missing amount never costs us the opportunity."""
from decimal import Decimal

import pytest

from openoutreach.funding.grants_gov import award_figures, describe_award

# Shape of a real fetchOpportunity synopsis (gid 362839, probed 2026-08-10) —
# Grants.gov returns every figure as a digit string.
SYNOPSIS = {
    "numberOfAwards": "7",
    "estimatedFunding": "2100000",
    "awardCeiling": "300000",
    "awardFloor": "150000",
}


def test_award_figures_reads_the_money_fields():
    figures = award_figures(SYNOPSIS)
    assert figures["ceiling"] == Decimal("300000")
    assert figures["floor"] == Decimal("150000")
    assert figures["estimated_funding"] == Decimal("2100000")
    assert figures["number_of_awards"] == 7


def test_amount_is_the_per_award_ceiling_not_the_program_pot():
    """funding_amount must be what one applicant could receive. Storing the
    program total would overstate every grant on the board."""
    assert award_figures(SYNOPSIS)["amount"] == Decimal("300000")


def test_amount_falls_back_to_floor_when_only_a_minimum_is_published():
    figures = award_figures({"awardFloor": "25000"})
    assert figures["amount"] == Decimal("25000")


def test_missing_and_zero_amounts_are_none_not_zero():
    """A published 0 means "not stated", and a 0 in funding_amount would read on
    the board as a real $0 grant."""
    for synopsis in ({}, {"awardCeiling": ""}, {"awardCeiling": "0"}, {"awardCeiling": None}):
        assert award_figures(synopsis)["amount"] is None


@pytest.mark.parametrize("junk", ["N/A", "see announcement", "$", "--", "abc"])
def test_unparseable_amounts_are_survived_not_raised(junk):
    assert award_figures({"awardCeiling": junk})["amount"] is None


def test_formatted_and_comma_separated_values_still_parse():
    assert award_figures({"awardCeiling": "$1,250,000"})["amount"] == Decimal("1250000")


def test_bad_number_of_awards_does_not_break_the_row():
    assert award_figures({"numberOfAwards": "several"})["number_of_awards"] is None


def test_describe_award_renders_a_range():
    note = describe_award(award_figures(SYNOPSIS))
    assert "$150,000-$300,000" in note
    assert "$2,100,000" in note
    assert "7 awards expected" in note


def test_describe_award_is_empty_when_nothing_is_published():
    assert describe_award(award_figures({})) == ""


def test_describe_award_collapses_an_equal_floor_and_ceiling():
    note = describe_award(award_figures({"awardCeiling": "50000", "awardFloor": "50000"}))
    assert note == "Award up to $50,000"
