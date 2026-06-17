from django.contrib.auth import get_user_model
from django.db import transaction

from openoutreach.core.models import Organization, Project
from openoutreach.funding.models import (
    Funder,
    GovernmentEntity,
    PartnerOrganization,
    ResourceProvider,
)
from openoutreach.signals.analysis_service import analyze_project
from openoutreach.signals.models import OrganizationAnalysisRun

DEMO_USERNAME = "missionsignal-demo"
DEMO_ORGANIZATION_NAME = "BridgeForward Digital Futures"
DEMO_WEBSITE = "https://bridgeforward.example.org"


def _seed_opportunity_database():
    funders = [
        {
            "name": "Cuyahoga Community Foundation",
            "funder_type": Funder.FunderType.COMMUNITY_FOUNDATION,
            "geography": ["Cleveland", "Cuyahoga County", "Ohio"],
            "focus_areas": ["workforce development", "digital equity", "youth development"],
            "beneficiaries": ["youth", "low-income residents", "job seekers"],
            "eligibility_notes": "Supports nonprofit programs serving Cleveland and Cuyahoga County residents.",
            "website": "https://cuyahoga-community-foundation.example.org",
            "notes": "Demo funder for BridgeForward-style local workforce and digital equity programs.",
        },
        {
            "name": "North Coast Corporate Giving Fund",
            "funder_type": Funder.FunderType.CORPORATE_FOUNDATION,
            "geography": ["Northeast Ohio", "Ohio"],
            "focus_areas": ["career readiness", "technology skills", "economic mobility"],
            "beneficiaries": ["students", "young adults", "underemployed residents"],
            "eligibility_notes": "Prioritizes employer-connected training and career pathway programs.",
            "website": "https://north-coast-giving.example.com",
            "notes": "Demo corporate foundation aligned with technology-enabled career pathways.",
        },
        {
            "name": "Ohio Workforce Innovation Fund",
            "funder_type": Funder.FunderType.STATE_GOVERNMENT,
            "geography": ["Ohio"],
            "focus_areas": ["workforce development", "credentials", "job placement"],
            "beneficiaries": ["job seekers", "young adults", "low-income residents"],
            "eligibility_notes": "Supports training programs with employer partnerships and measurable outcomes.",
            "website": "https://workforce-innovation.example.ohio.gov",
            "notes": "Demo state government funding lane for workforce readiness.",
        },
    ]
    for funder in funders:
        name = funder.pop("name")
        Funder.objects.update_or_create(name=name, defaults=funder)

    government_entities = [
        {
            "name": "City of Cleveland Youth and Workforce Office",
            "entity_type": GovernmentEntity.EntityType.CITY_GOVERNMENT,
            "geography": ["Cleveland", "Ohio"],
            "focus_areas": ["youth services", "workforce programs", "digital equity"],
            "department_or_office": "Youth and Workforce Office",
            "opportunity_lanes": ["City Grants", "Youth Services Funding", "RFPs / Procurement Opportunities"],
            "website": "https://cleveland-youth-workforce.example.gov",
            "notes": "Demo city office for local grants, service contracts, and youth workforce initiatives.",
        },
        {
            "name": "Cuyahoga County Workforce Partnership",
            "entity_type": GovernmentEntity.EntityType.WORKFORCE_DEVELOPMENT_BOARD,
            "geography": ["Cuyahoga County", "Ohio"],
            "focus_areas": ["workforce development", "career pathways", "employer partnerships"],
            "department_or_office": "Workforce Partnership",
            "opportunity_lanes": ["Workforce Programs", "Public-Sector Service Contracts"],
            "website": "https://cuyahoga-workforce.example.gov",
            "notes": "Demo workforce board for employer-aligned training and placement partnerships.",
        },
        {
            "name": "Cleveland Public Library Digital Access Team",
            "entity_type": GovernmentEntity.EntityType.PUBLIC_LIBRARY,
            "geography": ["Cleveland", "Ohio"],
            "focus_areas": ["digital equity", "technology training", "community learning"],
            "department_or_office": "Digital Access Team",
            "opportunity_lanes": ["Digital Equity Initiatives", "Community Development Programs"],
            "website": "https://cleveland-library-digital.example.org",
            "notes": "Demo library partner for digital access, workshops, and trusted community locations.",
        },
    ]
    for entity in government_entities:
        name = entity.pop("name")
        GovernmentEntity.objects.update_or_create(name=name, defaults=entity)

    resource_providers = [
        {
            "name": "Ohio Nonprofit Capacity Lab",
            "resource_type": ResourceProvider.ResourceType.CAPACITY_BUILDING_ORGANIZATION,
            "geography": ["Ohio"],
            "focus_areas": ["nonprofit capacity", "evaluation", "fundraising"],
            "resource_categories": ["Capacity Building Programs", "Training & Professional Development"],
            "eligibility_notes": "Serves nonprofits building program, fundraising, and evaluation capacity.",
            "website": "https://ohio-capacity-lab.example.org",
            "notes": "Demo capacity-building provider for organizational readiness.",
        },
        {
            "name": "Tech Access Donation Network",
            "resource_type": ResourceProvider.ResourceType.SOFTWARE_DONATION_PROGRAM,
            "geography": ["United States", "Ohio"],
            "focus_areas": ["technology", "software", "digital access"],
            "resource_categories": ["Software & Technology Resources", "Equipment & Infrastructure Resources"],
            "eligibility_notes": "Supports nonprofits with software donations and device-access planning.",
            "website": "https://tech-access-donations.example.org",
            "notes": "Demo technology resource provider for digital equity programs.",
        },
        {
            "name": "Cleveland Volunteer Connector",
            "resource_type": ResourceProvider.ResourceType.VOLUNTEER_NETWORK,
            "geography": ["Cleveland", "Cuyahoga County"],
            "focus_areas": ["volunteers", "mentoring", "community outreach"],
            "resource_categories": ["Volunteer Resources", "Training & Professional Development"],
            "eligibility_notes": "Connects local nonprofits with volunteers, mentors, and event support.",
            "website": "https://cleveland-volunteer-connector.example.org",
            "notes": "Demo volunteer network for mentoring and workshop support.",
        },
    ]
    for provider in resource_providers:
        name = provider.pop("name")
        ResourceProvider.objects.update_or_create(name=name, defaults=provider)

    partners = [
        {
            "name": "Cleveland Community College Career Pathways",
            "partner_type": PartnerOrganization.PartnerType.COMMUNITY_COLLEGE,
            "geography": ["Cleveland", "Ohio"],
            "focus_areas": ["career readiness", "credentials", "workforce training"],
            "beneficiaries": ["students", "young adults", "job seekers"],
            "collaboration_opportunities": ["credential pathways", "referrals", "shared training space"],
            "website": "https://cleveland-community-college.example.edu",
            "notes": "Demo community college partner for workforce credentials and career pathways.",
        },
        {
            "name": "Lakefront Employers Tech Council",
            "partner_type": PartnerOrganization.PartnerType.CORPORATE_PARTNER,
            "geography": ["Northeast Ohio"],
            "focus_areas": ["technology careers", "mentoring", "job placement"],
            "beneficiaries": ["interns", "young adults", "entry-level workers"],
            "collaboration_opportunities": ["mentors", "internships", "employer talks", "mock interviews"],
            "website": "https://lakefront-tech-council.example.com",
            "notes": "Demo corporate partner network for employer-connected programming.",
        },
        {
            "name": "Neighborhood Digital Inclusion Coalition",
            "partner_type": PartnerOrganization.PartnerType.NONPROFIT,
            "geography": ["Cleveland", "Cuyahoga County"],
            "focus_areas": ["digital equity", "community outreach", "device access"],
            "beneficiaries": ["low-income residents", "families", "job seekers"],
            "collaboration_opportunities": ["referrals", "outreach", "shared workshops", "device distribution"],
            "website": "https://neighborhood-digital-inclusion.example.org",
            "notes": "Demo nonprofit coalition partner for neighborhood-based digital equity work.",
        },
    ]
    for partner in partners:
        name = partner.pop("name")
        PartnerOrganization.objects.update_or_create(name=name, defaults=partner)


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
    _seed_opportunity_database()
    organization.refresh_from_db()
    project.refresh_from_db()
    return user, organization, project
