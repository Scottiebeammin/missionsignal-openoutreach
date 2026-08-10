"""budget_range is written by three different producers that never agreed on a
spelling — the intake form's display choices, the seed commands' tokens, and
older imports. These lock every spelling onto the same band."""
import pytest

from openoutreach.signals.foundations import (
    budget_target_amount,
    normalize_budget_range,
    peer_income_ceiling,
)

# (budget_range as stored, expected target, expected peer-income ceiling)
BANDS = [
    # Intake form display choices (signals.forms.OrganizationIntakeForm).
    ("Under $250K", 25_000, 5_000_000),
    ("$250K - $1M", 100_000, 20_000_000),
    ("$1M - $5M", 400_000, 100_000_000),
    ("$5M+", 1_000_000, None),
    # Seed-command tokens (seed_bam_orlando, seed_wotr, seed_egi, seed_tech_sassy_girlz).
    ("under_50k", 5_000, 1_000_000),
    ("under_250k", 25_000, 5_000_000),
    ("250k-1m", 100_000, 20_000_000),
    # Spellings seen in imported/dev rows.
    ("$250k-$1M", 100_000, 20_000_000),
    ("250K - 1M", 100_000, 20_000_000),
    ("under $50k", 5_000, 1_000_000),
]


@pytest.mark.parametrize("stored,target,ceiling", BANDS)
def test_every_spelling_lands_on_its_band(stored, target, ceiling):
    assert budget_target_amount(stored) == target
    assert peer_income_ceiling(stored) == ceiling


def test_intake_mid_band_is_not_swallowed_by_the_bare_250k_needle():
    """Regression: "$250K - $1M" used to miss the "250k - 1m" needle because of
    the "$" before "1M", fall through to bare "250k", and be sorted at the
    $25k band with no peer ceiling at all."""
    assert budget_target_amount("$250K - $1M") == 100_000
    assert budget_target_amount("$250K - $1M") != budget_target_amount("Under $250K")
    assert peer_income_ceiling("$250K - $1M") is not None


def test_1m_5m_is_not_read_as_5m_plus():
    """Regression: "$1M - $5M" matched the leading "5m" needle and was treated
    as a $5M+ organization — four times the correct grant target."""
    assert budget_target_amount("$1M - $5M") == 400_000
    assert budget_target_amount("$1M - $5M") != budget_target_amount("$5M+")


@pytest.mark.parametrize("blank", ["", "   ", None])
def test_blank_budget_has_no_target_or_ceiling(blank):
    assert budget_target_amount(blank) is None
    assert peer_income_ceiling(blank) is None


def test_unrecognized_value_is_not_forced_into_a_band():
    assert budget_target_amount("we don't publish this") is None
    assert peer_income_ceiling("we don't publish this") is None


def test_normalization_collapses_separators_and_currency():
    assert normalize_budget_range("$250K - $1M") == normalize_budget_range("250k-1m")
    assert normalize_budget_range("under_250k") == normalize_budget_range("Under $250K")
