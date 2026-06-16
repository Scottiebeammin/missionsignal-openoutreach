from django.db import transaction

from openoutreach.core.models import Organization, Project
from openoutreach.signals.models import OrganizationAnalysisRun


@transaction.atomic
def create_organization_intake(*, user, organization_name, website, mission, programs) -> Project:
    """Create an owned organization, its primary initiative, and pending analysis run."""
    organization = Organization.objects.create(
        name=organization_name,
        website=website,
        mission=mission,
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
        },
    )
    return project
