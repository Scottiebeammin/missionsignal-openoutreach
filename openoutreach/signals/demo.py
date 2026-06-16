from django.contrib.auth import get_user_model
from django.db import transaction

from openoutreach.core.models import Organization, Project
from openoutreach.signals.analysis_service import analyze_project
from openoutreach.signals.models import OrganizationAnalysisRun

DEMO_USERNAME = "missionsignal-demo"
DEMO_ORGANIZATION_NAME = "BridgeForward Digital Futures"
DEMO_WEBSITE = "https://bridgeforward.example.org"


@transaction.atomic
def seed_missionsignal_demo(*, password=None):
    """Create or refresh the deterministic MissionSignal demo records."""
    user, user_created = get_user_model().objects.get_or_create(username=DEMO_USERNAME)
    if password:
        user.set_password(password)
        user.save(update_fields=["password"])
    elif user_created:
        user.set_unusable_password()
        user.save(update_fields=["password"])

    organization, _ = Organization.objects.update_or_create(
        website=DEMO_WEBSITE,
        defaults={
            "name": DEMO_ORGANIZATION_NAME,
            "mission": (
                "Close the digital divide by preparing young people and adults "
                "from underserved communities for technology-enabled careers."
            ),
            "city": "Cleveland",
            "county": "Cuyahoga",
            "state": "Ohio",
            "service_area_notes": (
                "Serves Cleveland neighborhoods and nearby communities across "
                "Cuyahoga County, with priority for low-income residents."
            ),
        },
    )
    organization.users.add(user)

    project, _ = Project.objects.update_or_create(
        organization=organization,
        name="Primary Initiative",
        defaults={
            "programs": (
                "Digital skills workshops, youth career exploration, paid "
                "technology internships, device access, and employer-connected "
                "workforce training."
            ),
        },
    )
    project.users.add(user)

    if not OrganizationAnalysisRun.objects.filter(organization=organization).exists():
        OrganizationAnalysisRun.objects.create(
            organization=organization,
            input_snapshot={
                "organization_name": organization.name,
                "website": organization.website,
                "mission": organization.mission,
                "programs": project.programs,
            },
        )

    analyze_project(project, mode="deterministic")
    organization.refresh_from_db()
    project.refresh_from_db()
    return user, organization, project
