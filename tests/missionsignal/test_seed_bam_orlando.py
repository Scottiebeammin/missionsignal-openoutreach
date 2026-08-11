"""Last of the three seeds that populated capabilities but never project.programs,
which is the field Program Readiness actually scores."""
import pytest
from django.core.management import call_command

from openoutreach.core.models import Organization, Project
from openoutreach.signals.readiness import _has_text

pytestmark = pytest.mark.django_db


def _seed():
    call_command("seed_bam_orlando")
    org = Organization.objects.get(name__icontains="Black Architects")
    return org, Project.objects.get(organization=org)


def test_seed_populates_the_field_program_readiness_actually_scores():
    _, project = _seed()
    assert _has_text(project.programs), "empty programs scores 25 and reports a false gap"


def test_the_four_sourced_programs_are_named():
    _, project = _seed()
    for name in ("Design Workshops", "Site Tours", "Summer Youth Internships", "Scholarships"):
        assert name in project.programs
    assert len(project.program_summaries) == 4
    assert all(p["name"] and p["description"] for p in project.program_summaries)


def test_the_three_named_scholarships_survive():
    """Breaking Barriers, Rising Star Architect and Margaret Wells are named on
    their site — specific enough to be worth keeping through future edits."""
    _, project = _seed()
    blob = project.programs + " " + str(project.program_summaries)
    for award in ("Breaking Barriers", "Rising Star Architect", "Margaret Wells"):
        assert award in blob


def test_scholarship_names_do_not_become_separate_claims():
    """website_verification splits programs on "·". The three award names are
    comma-joined so they don't each become a half-sentence claim checked against
    the live site."""
    _, project = _seed()
    assert project.programs.count("·") == 3
    scholarships = project.programs.split("·")[-1]
    assert "Breaking Barriers" in scholarships and "Margaret Wells" in scholarships


def test_careersource_relationship_is_recorded():
    """A workforce-board partnership is a different funding signal from a
    community sponsor, and it is what delivers the internships."""
    org, _ = _seed()
    assert "CareerSource Central Florida" in org.existing_partnerships


def test_reseeding_is_idempotent_and_does_not_duplicate():
    _seed()
    _seed()
    assert Organization.objects.filter(name__icontains="Black Architects").count() == 1
