"""Program Readiness reads project.programs, not the organization summary. A seed
that describes programs only in organization_summary/capabilities still reports
"Programs need clearer definition" to a client whose website lists six of them."""
import pytest
from django.core.management import call_command

from openoutreach.core.models import Organization, Project
from openoutreach.signals.readiness import _has_text

pytestmark = pytest.mark.django_db


def _seed():
    call_command("seed_tech_sassy_girlz")
    org = Organization.objects.get(name="Tech Sassy Girlz")
    return org, Project.objects.get(organization=org)


def test_seed_populates_the_field_program_readiness_actually_scores():
    _, project = _seed()
    assert _has_text(project.programs), "empty programs scores 25 and reports a false gap"


def test_all_six_public_programs_are_named():
    _, project = _seed()
    for name in (
        "Tech Sassy Girlz Code",
        "Pearls in Tech Accelerator",
        "Tech Treks",
        "Tech Sassy Girlz Annual Conference",
        "Tech Your Impact",
        "Grow with Google",
    ):
        assert name in project.programs
    assert len(project.program_summaries) == 6
    assert all(p["name"] and p["description"] for p in project.program_summaries)


def test_programs_use_the_separator_website_verification_splits_on():
    """website_verification builds its claim list by splitting this field on
    [·,;\\n] — the wrong separator silently produces one giant claim."""
    _, project = _seed()
    assert project.programs.count("·") == 5


def test_reseeding_is_idempotent_and_does_not_duplicate():
    _seed()
    _seed()
    assert Organization.objects.filter(name="Tech Sassy Girlz").count() == 1
    org = Organization.objects.get(name="Tech Sassy Girlz")
    assert Project.objects.filter(organization=org).count() == 1


def test_budget_band_is_the_token_the_receipts_sort_matches():
    from openoutreach.signals.foundations import budget_target_amount, peer_income_ceiling

    org, _ = _seed()
    assert budget_target_amount(org.budget_range) == 100_000
    assert peer_income_ceiling(org.budget_range) == 20_000_000
