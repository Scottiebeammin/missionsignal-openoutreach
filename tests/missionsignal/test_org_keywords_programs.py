"""org_keywords reads the programmes an organization actually runs.

Women on the Rise made the gap visible. Their mission field holds their real
73-character tagline, so they scored 26 keywords against 37-43 for the other two
founding partners and the thinness looked like an unfilled profile. It was not: their
programmes were recorded on the project all along and the matcher never read them.
Including `project.programs` took them to 43 keywords and 41 -> 48 relevant rows.

The alternative was rewriting a real client's mission statement, which would have put
our prose in their record in place of their own words.
"""
import pytest

from openoutreach.core.models import Organization, Project
from openoutreach.funding.relevance import org_keywords


@pytest.fixture
def wotr_shaped(db):
    """A short-tagline org with rich programme text — the shape that was losing out."""
    organization = Organization.objects.create(
        name="Women on the Rise (test double)",
        website="https://example.invalid",
        # A real tagline: short on purpose, not an unfilled field.
        mission="Inspiring societies where equality exists in all facets of women's lives.",
        city="Orlando",
        county="Orange",
        state="Florida",
        focus_areas=["career development", "financial literacy"],
        beneficiaries=["women"],
    )
    project = Project.objects.create(
        organization=organization,
        name="Opportunity Web",
        programs=(
            "Career Development Cohort · Financial Empowerment Series · "
            "Entrepreneurship Showcase · Executive Roundtable"
        ),
    )
    return organization, project


@pytest.mark.django_db
def test_programs_widen_the_vocabulary(wotr_shaped):
    organization, project = wotr_shaped

    without = org_keywords(organization)
    with_programs = org_keywords(organization, project)

    assert len(with_programs) > len(without)
    # Terms that exist ONLY in the programmes text.
    assert "entrepreneurship" in with_programs
    assert "roundtable" in with_programs
    assert "entrepreneurship" not in without


@pytest.mark.django_db
def test_existing_vocabulary_is_preserved(wotr_shaped):
    """Additive only — passing a project must never drop a term."""
    organization, project = wotr_shaped

    assert org_keywords(organization) <= org_keywords(organization, project)


@pytest.mark.django_db
def test_project_argument_is_optional(wotr_shaped):
    """The seven existing call sites kept working because project defaults to None."""
    organization, _project = wotr_shaped

    assert org_keywords(organization)  # no second argument, no error


@pytest.mark.django_db
def test_empty_programs_is_harmless(db):
    organization = Organization.objects.create(
        name="Blank Programs Org",
        website="https://example.invalid",
        mission="Youth development in Central Florida.",
        focus_areas=["youth development"],
    )
    project = Project.objects.create(organization=organization, name="P", programs="")

    assert org_keywords(organization, project) == org_keywords(organization)
