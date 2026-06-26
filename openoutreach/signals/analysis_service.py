from django.db import transaction
from django.utils import timezone

from openoutreach.core.models import Organization
from openoutreach.funding.models import FundingCriteria
from openoutreach.signals.analyzer import OrganizationAnalyzerInput, analyze_deterministically
from openoutreach.signals.models import OrganizationAnalysisRun
from openoutreach.signals.website_scraper import scrape_website_text


@transaction.atomic
def analyze_project(project, *, mode="deterministic"):
    """Analyze a project's organization and create or update its FundingCriteria."""
    if mode != "deterministic":
        raise ValueError(f"Unsupported organization analyzer mode: {mode}")

    organization = Organization.objects.select_for_update().get(pk=project.organization_id)

    # Scrape website text to enrich focus/beneficiary detection.
    # Done outside the transaction-save path so a slow/failed fetch never
    # blocks the analysis run from being recorded.
    website_text = scrape_website_text(organization.website)

    # Pull intake notes from the project's primary member if present.
    intake_notes = project.intake_notes or ""

    data = OrganizationAnalyzerInput(
        organization_name=organization.name,
        website=organization.website,
        mission=organization.mission,
        programs=project.programs,
        organization_type=organization.organization_type or "",
        city=organization.city,
        county=organization.county,
        state=organization.state,
        service_area_notes=organization.service_area_notes,
        outcomes_and_impact=organization.outcomes_and_impact,
        budget_range=organization.budget_range,
        current_funding_sources=organization.current_funding_sources,
        existing_partnerships=organization.existing_partnerships,
        website_text=website_text,
        intake_notes=intake_notes,
        focus_area_selections=list(organization.focus_areas or []),
        beneficiary_selections=list(organization.beneficiaries or []),
    )
    run = (
        OrganizationAnalysisRun.objects.filter(
            organization=organization, status=OrganizationAnalysisRun.Status.PENDING,
        )
        .order_by("-created_at")
        .first()
    )
    if run is None:
        run = OrganizationAnalysisRun(organization=organization)
    run.status = OrganizationAnalysisRun.Status.RUNNING
    run.analyzer_version = "deterministic-mvp-v2"
    run.input_snapshot = data.model_dump()
    run.started_at = timezone.now()
    run.save()

    output = analyze_deterministically(data)
    organization.organization_summary = output.organization_summary
    organization.focus_areas = output.focus_areas
    organization.beneficiaries = output.beneficiaries
    organization.service_geographies = output.service_geographies
    organization.capabilities = output.capabilities
    organization.outcomes_and_impact = output.outcomes_and_impact
    organization.search_keywords = output.search_keywords
    organization.analysis_warnings = output.analysis_warnings
    organization.analysis_confidence = output.analysis_confidence
    organization.analysis_status = (
        Organization.AnalysisStatus.PARTIAL
        if output.analysis_warnings
        else Organization.AnalysisStatus.READY
    )
    organization.analyzer_version = run.analyzer_version
    organization.last_analyzed_at = timezone.now()
    organization.save(update_fields=[
        "organization_summary", "focus_areas", "beneficiaries", "service_geographies",
        "capabilities", "outcomes_and_impact", "search_keywords", "analysis_warnings",
        "analysis_confidence", "analysis_status", "analyzer_version", "last_analyzed_at",
    ])

    criteria_data = output.funding_criteria
    criteria, _ = FundingCriteria.objects.update_or_create(
        project=project,
        defaults={
            "focus_areas": criteria_data.focus_areas,
            "beneficiaries": criteria_data.beneficiaries,
            "eligible_geographies": criteria_data.eligible_geographies,
            "program_areas": criteria_data.program_areas,
            "funding_use_categories": criteria_data.funding_use_categories,
            "likely_funder_types": criteria_data.likely_funder_types,
            "likely_opportunity_types": criteria_data.likely_opportunity_types,
            "inclusion_criteria": criteria_data.inclusion_criteria,
            "analyzer_confidence": output.analysis_confidence,
            "source_analysis_run": run,
        },
    )

    run.status = (
        OrganizationAnalysisRun.Status.PARTIAL
        if output.analysis_warnings
        else OrganizationAnalysisRun.Status.COMPLETED
    )
    run.output_snapshot = output.model_dump()
    run.warnings = output.analysis_warnings
    run.completed_at = timezone.now()
    run.save(update_fields=["status", "output_snapshot", "warnings", "completed_at"])
    return output, criteria, run
