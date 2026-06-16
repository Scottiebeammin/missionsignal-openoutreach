from django.db import transaction

from openoutreach.core.models import Organization, Project
from openoutreach.signals.models import OrganizationAnalysisRun


@transaction.atomic
def create_organization_intake(
    *,
    user,
    organization_name,
    website,
    mission,
    programs,
    organization_type="",
    city="",
    county="",
    state="",
    service_area_notes="",
    outcomes_and_impact=None,
    budget_range="",
    current_funding_sources=None,
    existing_partnerships=None,
) -> Project:
    """Create an owned organization, its primary initiative, and pending analysis run."""
    organization = Organization.objects.create(
        name=organization_name,
        website=website,
        mission=mission,
        organization_type=organization_type or None,
        city=city,
        county=county,
        state=state,
        service_area_notes=service_area_notes,
        outcomes_and_impact=outcomes_and_impact or [],
        budget_range=budget_range,
        current_funding_sources=current_funding_sources or [],
        existing_partnerships=existing_partnerships or [],
    )
    organization.users.add(user)

    project = Project.objects.create(
        organization=organization,
        name="Primary Initiative",
        programs=programs,
    )
    project.users.add(user)

    OrganizationAnalysisRun.objects.create(
        organization=organization,
        input_snapshot={
            "organization_name": organization.name,
            "website": organization.website,
            "mission": organization.mission,
            "programs": project.programs,
            "organization_type": organization.organization_type,
            "city": organization.city,
            "county": organization.county,
            "state": organization.state,
            "service_area_notes": organization.service_area_notes,
            "outcomes_and_impact": organization.outcomes_and_impact,
            "budget_range": organization.budget_range,
            "current_funding_sources": organization.current_funding_sources,
            "existing_partnerships": organization.existing_partnerships,
        },
    )
    return project
