"""WOTR is a live founding partner and read "Programs need clearer definition" on
its own Readiness page from July until this was fixed — the seed populated
capabilities but never project.programs, which is the field the score reads.
"""
import pytest
from django.core.management import call_command

from openoutreach.core.models import Organization, Project
from openoutreach.signals.readiness import _has_text

pytestmark = pytest.mark.django_db


def _seed():
    call_command("seed_wotr")
    org = Organization.objects.get(name="Women on the Rise International, Inc.")
    return org, Project.objects.get(organization=org)


def test_seed_populates_the_field_program_readiness_actually_scores():
    _, project = _seed()
    assert _has_text(project.programs), "empty programs scores 25 and reports a false gap"


def test_the_six_sourced_programs_are_named():
    _, project = _seed()
    for name in (
        "Career Development Cohort",
        "Educated & Broke",
        "Entrepreneurship Showcase: Built With Intention",
        "The RISE Executive Roundtable",
        "Self Care Awareness Assessment",
        "Annual Awards Gala",
    ):
        assert name in project.programs
    assert len(project.program_summaries) == 6
    assert all(p["name"] and p["description"] for p in project.program_summaries)


def test_programs_use_the_separator_website_verification_splits_on():
    """website_verification builds its claim list by splitting this field on
    [·,;\\n]; the wrong separator silently produces one giant claim."""
    _, project = _seed()
    assert project.programs.count("·") == 5


def test_the_four_pillars_are_still_represented():
    """Their stated model is financial literacy, career development,
    entrepreneurship and personal wellness — each should have a program behind it."""
    _, project = _seed()
    blob = (project.programs + " " + str(project.program_summaries)).lower()
    for pillar in ("financial", "career", "entrepreneur", "self care"):
        assert pillar in blob


def test_reseeding_is_idempotent_and_does_not_duplicate():
    _seed()
    _seed()
    org = Organization.objects.get(name="Women on the Rise International, Inc.")
    assert Organization.objects.filter(name="Women on the Rise International, Inc.").count() == 1
    assert Project.objects.filter(organization=org).count() == 1
