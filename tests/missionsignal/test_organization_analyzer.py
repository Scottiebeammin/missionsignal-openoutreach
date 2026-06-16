import pytest

from openoutreach.core.models import Organization, Project
from openoutreach.funding.models import FundingCriteria
from openoutreach.signals.analysis_service import analyze_project
from openoutreach.signals.analyzer import (
    OrganizationAnalyzerInput,
    OrganizationAnalyzerOutput,
    analyze_deterministically,
)
from openoutreach.signals.models import OrganizationAnalysisRun


pytestmark = pytest.mark.django_db


@pytest.fixture
def project():
    organization = Organization.objects.create(
        name="Mission Works",
        website="https://mission.example.org",
        mission="Improve economic mobility for young people.",
        city="Detroit",
        county="Wayne County",
        state="Michigan",
        service_area_notes="Serving neighborhoods across Wayne County.",
    )
    return Project.objects.create(
        organization=organization,
        name="Primary Initiative",
        programs="Youth career training and small business coaching.",
    )


def test_deterministic_analyzer_returns_structured_output():
    result = analyze_deterministically(OrganizationAnalyzerInput(
        organization_name="Mission Works",
        website="https://mission.example.org",
        mission="Improve economic mobility for youth.",
        programs="Career training and small business coaching.",
        city="Detroit",
        state="Michigan",
    ))
    assert isinstance(result, OrganizationAnalyzerOutput)
    assert "workforce development" in result.focus_areas
    assert "youth" in result.beneficiaries
    assert result.service_geographies == ["Detroit", "Michigan"]
    assert result.analysis_confidence > 0
    assert result.funding_criteria.focus_areas == result.focus_areas


def test_deterministic_analyzer_uses_optional_readiness_profile_fields():
    result = analyze_deterministically(OrganizationAnalyzerInput(
        organization_name="Mission Works",
        website="https://mission.example.org",
        mission="Improve economic mobility for youth.",
        programs="Career training and small business coaching.",
        organization_type="Nonprofit",
        city="Detroit",
        state="Michigan",
        outcomes_and_impact=["85% completion rate", "120 graduates"],
        budget_range="$250K - $1M",
        current_funding_sources=["Community Foundation"],
        existing_partnerships=["Local College"],
    ))

    assert result.outcomes_and_impact == ["85% completion rate", "120 graduates"]
    assert "Nonprofit" in result.funding_criteria.inclusion_criteria
    assert "85% completion rate" in result.funding_criteria.inclusion_criteria
    assert not any("Outcomes and impact require" in warning for warning in result.analysis_warnings)
    assert not any("Budget range" in warning for warning in result.analysis_warnings)
    assert not any("Current funding sources" in warning for warning in result.analysis_warnings)
    assert not any("Existing partnerships" in warning for warning in result.analysis_warnings)


def test_analysis_updates_organization_profile(project):
    output, _criteria, run = analyze_project(project)
    organization = project.organization
    organization.refresh_from_db()
    assert organization.organization_summary == output.organization_summary
    assert organization.focus_areas == output.focus_areas
    assert organization.beneficiaries == output.beneficiaries
    assert organization.service_geographies == output.service_geographies
    assert organization.capabilities == output.capabilities
    assert organization.search_keywords == output.search_keywords
    assert organization.analysis_warnings == output.analysis_warnings
    assert organization.analysis_confidence == output.analysis_confidence
    assert organization.analysis_status == Organization.AnalysisStatus.PARTIAL
    assert organization.analyzer_version == "deterministic-mvp-v1"
    assert organization.last_analyzed_at is not None
    assert run.status == OrganizationAnalysisRun.Status.PARTIAL


def test_analysis_creates_and_then_updates_funding_criteria(project):
    output, criteria, first_run = analyze_project(project)
    assert FundingCriteria.objects.filter(project=project).count() == 1
    assert criteria.focus_areas == output.funding_criteria.focus_areas
    assert criteria.beneficiaries == output.funding_criteria.beneficiaries
    assert criteria.eligible_geographies == output.funding_criteria.eligible_geographies
    assert criteria.source_analysis_run == first_run

    project.programs = "Youth career training, food access, and community outreach."
    project.save(update_fields=["programs"])
    second_output, updated, second_run = analyze_project(project)
    assert FundingCriteria.objects.filter(project=project).count() == 1
    assert updated.pk == criteria.pk
    assert updated.focus_areas == second_output.funding_criteria.focus_areas
    assert updated.source_analysis_run == second_run


def test_missing_optional_location_fields_produce_warning_not_failure():
    organization = Organization.objects.create(
        name="Mission Works",
        website="https://mission.example.org",
        mission="Provide youth education.",
    )
    project = Project.objects.create(
        organization=organization,
        name="Primary Initiative",
        programs="Youth learning programs.",
    )
    output, criteria, run = analyze_project(project)
    assert output.service_geographies == []
    assert any("location" in warning for warning in output.analysis_warnings)
    assert any("Budget range" in warning for warning in output.analysis_warnings)
    assert any("Current funding sources" in warning for warning in output.analysis_warnings)
    assert any("Existing partnerships" in warning for warning in output.analysis_warnings)
    assert output.analysis_confidence > 0
    assert criteria.eligible_geographies == []
    assert run.status == OrganizationAnalysisRun.Status.PARTIAL


def test_analysis_reuses_pending_intake_run(project):
    pending = OrganizationAnalysisRun.objects.create(
        organization=project.organization,
        input_snapshot={"source": "intake"},
    )
    _output, _criteria, run = analyze_project(project)
    assert run.pk == pending.pk
    assert OrganizationAnalysisRun.objects.filter(organization=project.organization).count() == 1


def test_unsupported_analyzer_mode_fails_before_writing(project):
    with pytest.raises(ValueError, match="Unsupported organization analyzer mode"):
        analyze_project(project, mode="external")
    assert FundingCriteria.objects.filter(project=project).count() == 0
    assert OrganizationAnalysisRun.objects.filter(organization=project.organization).count() == 0
