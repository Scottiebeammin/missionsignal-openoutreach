from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from datetime import date

from openoutreach.core.models import Organization, Project
from openoutreach.funding.models import (
    DocumentVaultItem,
    EvidenceLibraryItem,
    Funder,
    GovernmentEntity,
    Opportunity,
    PartnerOrganization,
    ResourceProvider,
    SourceOrganization,
)
from openoutreach.signals.documents import ensure_opportunity_document_requirements
from openoutreach.signals.analysis_service import analyze_project
from openoutreach.signals.models import (
    Celebration,
    OrganizationAnalysisRun,
    OrganizationContact,
    PartnerOrganization as RelationshipPartnerOrganization,
)

DEMO_USERNAME = "missionsignal-demo"
DEMO_ORGANIZATION_NAME = "Bright Future Youth Collective"
DEMO_WEBSITE = "https://brightfutureyouth.example.org"


def _seed_opportunity_database():
    reviewed_at = timezone.now()
    funders = [
        {
            "name": "Orange Community Foundation",
            "funder_type": Funder.FunderType.COMMUNITY_FOUNDATION,
            "geography": ["Orlando", "Orange County", "Florida"],
            "focus_areas": ["workforce development", "youth opportunity", "youth development"],
            "beneficiaries": ["youth", "low-income residents", "job seekers"],
            "eligibility_notes": "Supports nonprofit programs serving Orlando and Orange County residents.",
            "website": "https://Orange-community-foundation.example.org",
            "notes": "Demo funder for Bright Future Youth Collective-style local workforce and youth opportunity programs.",
        },
        {
            "name": "Central Florida Corporate Giving Fund",
            "funder_type": Funder.FunderType.CORPORATE_FOUNDATION,
            "geography": ["Central Florida", "Florida"],
            "focus_areas": ["career readiness", "technology skills", "economic mobility"],
            "beneficiaries": ["students", "young adults", "underemployed residents"],
            "eligibility_notes": "Prioritizes employer-connected training and career pathway programs.",
            "website": "https://north-coast-giving.example.com",
            "notes": "Demo corporate foundation aligned with technology-enabled career pathways.",
        },
        {
            "name": "Florida Workforce Innovation Fund",
            "funder_type": Funder.FunderType.STATE_GOVERNMENT,
            "geography": ["Florida"],
            "focus_areas": ["workforce development", "credentials", "job placement"],
            "beneficiaries": ["job seekers", "young adults", "low-income residents"],
            "eligibility_notes": "Supports training programs with employer partnerships and measurable outcomes.",
            "website": "https://workforce-innovation.example.Florida.gov",
            "notes": "Demo state government funding lane for workforce readiness.",
        },
        {
            "name": "Everglades Environmental Justice Fund",
            "funder_type": Funder.FunderType.FAMILY_FOUNDATION,
            "geography": ["Florida", "Regional"],
            "focus_areas": ["environmental justice", "youth development", "community development"],
            "beneficiaries": ["youth", "residents", "community organizations"],
            "eligibility_notes": "Supports place-based environmental justice, civic learning, and stewardship programs.",
            "website": "https://lake-erie-ej.example.org",
            "notes": "Named environmental funder for stewardship and youth civic lab pathways.",
        },
        {
            "name": "Greater Orlando Food Security Fund",
            "funder_type": Funder.FunderType.COMMUNITY_FOUNDATION,
            "geography": ["Orlando", "Orange County"],
            "focus_areas": ["food security", "community development", "volunteer resources"],
            "beneficiaries": ["families", "low-income residents", "seniors"],
            "eligibility_notes": "Supports neighborhood food access, distribution partnerships, and resident support programs.",
            "website": "https://Orlando-food-security-fund.example.org",
            "notes": "Named food security funder for adjacent community support pathways.",
        },
        {
            "name": "Central Florida Health Equity Foundation",
            "funder_type": Funder.FunderType.FAMILY_FOUNDATION,
            "geography": ["Florida", "Regional"],
            "focus_areas": ["healthcare", "mental health", "community health"],
            "beneficiaries": ["patients", "families", "low-income residents"],
            "eligibility_notes": "Funds public health, wellness, access, and community benefit partnerships.",
            "website": "https://north-coast-health-equity.example.org",
            "notes": "Named health funder for community health validation profiles.",
        },
        {
            "name": "Florida Education Pathways Fund",
            "funder_type": Funder.FunderType.CORPORATE_FOUNDATION,
            "geography": ["Florida"],
            "focus_areas": ["education", "career readiness", "youth development"],
            "beneficiaries": ["students", "youth", "young adults"],
            "eligibility_notes": "Supports school-linked education, career exploration, and youth advancement programs.",
            "website": "https://Florida-education-pathways.example.org",
            "notes": "Named education funder for youth development and career readiness pathways.",
        },
        {
            "name": "United Way of Greater Orlando",
            "funder_type": Funder.FunderType.UNITED_WAY,
            "geography": ["Orlando", "Orange County"],
            "focus_areas": ["youth development", "housing", "food security", "community development"],
            "beneficiaries": ["families", "youth", "low-income residents"],
            "eligibility_notes": "Supports community partners addressing basic needs, youth outcomes, and resident stability.",
            "website": "https://united-way-Orlando.example.org",
            "notes": "Named United Way chapter for multi-sector nonprofit validation.",
        },
        {
            "name": "Central Florida Corporate Giving Program",
            "funder_type": Funder.FunderType.CORPORATE_FOUNDATION,
            "geography": ["Regional", "Florida"],
            "focus_areas": ["workforce development", "volunteer resources", "sponsorships"],
            "beneficiaries": ["students", "job seekers", "community organizations"],
            "eligibility_notes": "Supports employer-connected sponsorships, volunteer engagement, and skills programs.",
            "website": "https://great-lakes-giving.example.com",
            "notes": "Named corporate giving program for sponsorship and employer pathways.",
        },
    ]
    for funder in funders:
        name = funder.pop("name")
        funder.setdefault("intelligence_status", Funder.IntelligenceStatus.ACTIVE)
        funder.setdefault("source_references", [
            {"title": f"{name} public funding profile", "source": "Demo research note"},
        ])
        funder.setdefault("source_urls", [funder.get("website", "")] if funder.get("website") else [])
        funder.setdefault("source_notes", f"Reviewed demo intelligence profile for {name}.")
        funder.setdefault("verification_status", Funder.VerificationStatus.REVIEWED)
        funder.setdefault("last_reviewed_at", reviewed_at)
        Funder.objects.update_or_create(name=name, defaults=funder)

    government_entities = [
        {
            "name": "City of Orlando Youth and Workforce Office",
            "entity_type": GovernmentEntity.EntityType.CITY_GOVERNMENT,
            "geography": ["Orlando", "Florida"],
            "focus_areas": ["youth services", "workforce programs", "youth opportunity"],
            "department_or_office": "Youth and Workforce Office",
            "opportunity_lanes": ["City Grants", "Youth Services Funding", "RFPs / Procurement Opportunities"],
            "website": "https://Orlando-youth-workforce.example.gov",
            "notes": "Demo city office for local grants, service contracts, and youth workforce initiatives.",
        },
        {
            "name": "Orange County Workforce Partnership",
            "entity_type": GovernmentEntity.EntityType.WORKFORCE_DEVELOPMENT_BOARD,
            "geography": ["Orange County", "Florida"],
            "focus_areas": ["workforce development", "career pathways", "employer partnerships"],
            "department_or_office": "Workforce Partnership",
            "opportunity_lanes": ["Workforce Programs", "Public-Sector Service Contracts"],
            "website": "https://Orange-workforce.example.gov",
            "notes": "Demo workforce board for employer-aligned training and placement partnerships.",
        },
        {
            "name": "Orlando Public Library Youth Access Team",
            "entity_type": GovernmentEntity.EntityType.PUBLIC_LIBRARY,
            "geography": ["Orlando", "Florida"],
            "focus_areas": ["youth opportunity", "technology training", "community learning"],
            "department_or_office": "Youth Access Team",
            "opportunity_lanes": ["Youth Opportunity Initiatives", "Community Development Programs"],
            "website": "https://Orlando-library-digital.example.org",
            "notes": "Demo library partner for youth access, workshops, and trusted community locations.",
        },
    ]
    for entity in government_entities:
        name = entity.pop("name")
        GovernmentEntity.objects.update_or_create(name=name, defaults=entity)

    resource_providers = [
        {
            "name": "Florida Nonprofit Capacity Lab",
            "resource_type": ResourceProvider.ResourceType.CAPACITY_BUILDING_ORGANIZATION,
            "geography": ["Florida"],
            "focus_areas": ["nonprofit capacity", "evaluation", "fundraising"],
            "resource_categories": ["Capacity Building Programs", "Training & Professional Development"],
            "eligibility_notes": "Serves nonprofits building program, fundraising, and evaluation capacity.",
            "website": "https://Florida-capacity-lab.example.org",
            "notes": "Demo capacity-building provider for organizational readiness.",
        },
        {
            "name": "Tech Access Donation Network",
            "resource_type": ResourceProvider.ResourceType.SOFTWARE_DONATION_PROGRAM,
            "geography": ["United States", "Florida"],
            "focus_areas": ["technology", "software", "youth access"],
            "resource_categories": ["Software & Technology Resources", "Equipment & Infrastructure Resources"],
            "eligibility_notes": "Supports nonprofits with software donations and device-access planning.",
            "website": "https://tech-access-donations.example.org",
            "notes": "Demo technology resource provider for youth opportunity programs.",
        },
        {
            "name": "Orlando Volunteer Connector",
            "resource_type": ResourceProvider.ResourceType.VOLUNTEER_NETWORK,
            "geography": ["Orlando", "Orange County"],
            "focus_areas": ["volunteers", "mentoring", "community outreach"],
            "resource_categories": ["Volunteer Resources", "Training & Professional Development"],
            "eligibility_notes": "Connects local nonprofits with volunteers, mentors, and event support.",
            "website": "https://Orlando-volunteer-connector.example.org",
            "notes": "Demo volunteer network for mentoring and workshop support.",
        },
    ]
    for provider in resource_providers:
        name = provider.pop("name")
        ResourceProvider.objects.update_or_create(name=name, defaults=provider)

    partners = [
        {
            "name": "Orlando Community College Career Pathways",
            "partner_type": PartnerOrganization.PartnerType.COMMUNITY_COLLEGE,
            "geography": ["Orlando", "Florida"],
            "focus_areas": ["career readiness", "credentials", "workforce training"],
            "beneficiaries": ["students", "young adults", "job seekers"],
            "collaboration_opportunities": ["credential pathways", "referrals", "shared training space"],
            "website": "https://Orlando-community-college.example.edu",
            "notes": "Demo community college partner for workforce credentials and career pathways.",
        },
        {
            "name": "Lakefront Employers Tech Council",
            "partner_type": PartnerOrganization.PartnerType.CORPORATE_PARTNER,
            "geography": ["Central Florida"],
            "focus_areas": ["technology careers", "mentoring", "job placement"],
            "beneficiaries": ["interns", "young adults", "entry-level workers"],
            "collaboration_opportunities": ["mentors", "internships", "employer talks", "mock interviews"],
            "website": "https://lakefront-tech-council.example.com",
            "notes": "Demo corporate partner network for employer-connected programming.",
        },
        {
            "name": "Neighborhood Youth Inclusion Coalition",
            "partner_type": PartnerOrganization.PartnerType.NONPROFIT,
            "geography": ["Orlando", "Orange County"],
            "focus_areas": ["youth opportunity", "community outreach", "device access"],
            "beneficiaries": ["low-income residents", "families", "job seekers"],
            "collaboration_opportunities": ["referrals", "outreach", "shared workshops", "device distribution"],
            "website": "https://neighborhood-digital-inclusion.example.org",
            "notes": "Demo nonprofit coalition partner for neighborhood-based youth opportunity work.",
        },
    ]
    for partner in partners:
        name = partner.pop("name")
        partner.setdefault("intelligence_status", PartnerOrganization.IntelligenceStatus.ACTIVE)
        partner.setdefault("mission_alignment_notes", f"{name} has direct mission alignment with Bright Future Youth Collective's youth development model.")
        partner.setdefault("opportunity_notes", "Useful for named partnership recommendations and future pathway development.")
        partner.setdefault("relationship_notes", "Prioritize outreach when a pathway needs credible local partner evidence.")
        partner.setdefault("source_references", [
            {"title": f"{name} partner profile", "source": "Demo research note"},
        ])
        partner.setdefault("source_urls", [partner.get("website", "")] if partner.get("website") else [])
        partner.setdefault("source_notes", f"Reviewed ecosystem organization profile for {name}.")
        partner.setdefault("verification_status", PartnerOrganization.VerificationStatus.REVIEWED)
        partner.setdefault("last_reviewed_at", reviewed_at)
        PartnerOrganization.objects.update_or_create(name=name, defaults=partner)

    source_organizations = [
        {
            "name": "Orange Community Foundation",
            "organization_type": SourceOrganization.OrganizationType.FOUNDATION,
            "website": "https://Orange-community-foundation.example.org",
            "geography": ["Orlando", "Orange County", "Florida"],
            "notes": "Local foundation focused on youth, workforce, youth opportunity, and community development.",
        },
        {
            "name": "Florida Workforce Innovation Fund",
            "organization_type": SourceOrganization.OrganizationType.WORKFORCE_BOARD,
            "website": "https://workforce-innovation.example.Florida.gov",
            "geography": ["Florida"],
            "notes": "Statewide workforce funder for credentials, placement, and employer partnerships.",
        },
        {
            "name": "City of Orlando Youth and Workforce Office",
            "organization_type": SourceOrganization.OrganizationType.GOVERNMENT_AGENCY,
            "website": "https://Orlando-youth-workforce.example.gov",
            "geography": ["Orlando", "Florida"],
            "notes": "City office managing youth services, workforce programs, contracts, and local RFPs.",
        },
        {
            "name": "Neighborhood Youth Inclusion Coalition",
            "organization_type": SourceOrganization.OrganizationType.NONPROFIT,
            "website": "https://neighborhood-digital-inclusion.example.org",
            "geography": ["Orlando", "Orange County"],
            "notes": "Community coalition for outreach, device access, and youth opportunity partnerships.",
        },
        {
            "name": "Florida Nonprofit Capacity Lab",
            "organization_type": SourceOrganization.OrganizationType.RESOURCE_PROVIDER,
            "website": "https://Florida-capacity-lab.example.org",
            "geography": ["Florida"],
            "notes": "Capacity-building provider for evaluation, fundraising, and nonprofit operations.",
        },
        {
            "name": "Central Florida Corporate Citizenship Council",
            "organization_type": SourceOrganization.OrganizationType.CORPORATE_PARTNER,
            "website": "https://great-lakes-citizenship.example.com",
            "geography": ["Regional", "Florida"],
            "notes": "Corporate social impact network supporting sponsorships and volunteer engagement.",
        },
        {
            "name": "Southeast Arts and Culture Trust",
            "organization_type": SourceOrganization.OrganizationType.FOUNDATION,
            "website": "https://Southeast-arts-trust.example.org",
            "geography": ["Regional"],
            "notes": "Regional foundation focused on arts, culture, and creative placemaking.",
        },
        {
            "name": "National Rural Health Collaborative",
            "organization_type": SourceOrganization.OrganizationType.NONPROFIT,
            "website": "https://rural-health-collab.example.org",
            "geography": ["National"],
            "notes": "National collaborative focused on rural health and healthcare access.",
        },
        {
            "name": "University Of Central Florida Civic Innovation Center",
            "organization_type": SourceOrganization.OrganizationType.UNIVERSITY,
            "website": "https://civic-innovation.example.edu",
            "geography": ["Orlando", "Florida"],
            "notes": "University center supporting applied research, training, and civic technology.",
        },
        {
            "name": "Orange Housing Stability Office",
            "organization_type": SourceOrganization.OrganizationType.GOVERNMENT_AGENCY,
            "website": "https://housing-stability.example.gov",
            "geography": ["Orange County", "Florida"],
            "notes": "County agency focused on housing stability and community development.",
        },
        {
            "name": "Florida Veterans Community Fund",
            "organization_type": SourceOrganization.OrganizationType.FOUNDATION,
            "website": "https://Florida-veterans-community.example.org",
            "geography": ["Florida"],
            "notes": "Foundation focused on veterans, housing stability, mental health, and workforce transition.",
        },
        {
            "name": "Rainbow Community Wellness Coalition",
            "organization_type": SourceOrganization.OrganizationType.NONPROFIT,
            "website": "https://rainbow-wellness.example.org",
            "geography": ["Orlando", "Florida"],
            "notes": "Coalition supporting LGBTQ+ youth, mental health, and community-based wellness programs.",
        },
        {
            "name": "Access Forward Disability Network",
            "organization_type": SourceOrganization.OrganizationType.NONPROFIT,
            "website": "https://access-forward.example.org",
            "geography": ["Florida", "Regional"],
            "notes": "Network focused on disability access, inclusive employment, and assistive technology.",
        },
        {
            "name": "Greater Orlando Food Security Alliance",
            "organization_type": SourceOrganization.OrganizationType.NONPROFIT,
            "website": "https://Orlando-food-security.example.org",
            "geography": ["Orlando", "Orange County"],
            "notes": "Alliance coordinating food security, nutrition, and community distribution programs.",
        },
        {
            "name": "Second Chance Reentry Collaborative",
            "organization_type": SourceOrganization.OrganizationType.NONPROFIT,
            "website": "https://second-chance-reentry.example.org",
            "geography": ["Orange County", "Florida"],
            "notes": "Collaborative supporting reentry, justice-involved residents, workforce transition, and housing navigation.",
        },
        {
            "name": "Everglades Environmental Justice Fund",
            "organization_type": SourceOrganization.OrganizationType.FOUNDATION,
            "website": "https://lake-erie-ej.example.org",
            "geography": ["Regional", "Florida"],
            "notes": "Foundation focused on environmental justice, climate resilience, and community development.",
        },
    ]
    sources = {}
    for source in source_organizations:
        name = source.pop("name")
        source.setdefault("source_urls", [source.get("website", "")] if source.get("website") else [])
        source.setdefault("source_notes", f"Reviewed source organization profile for {name}.")
        source.setdefault("verification_status", SourceOrganization.VerificationStatus.REVIEWED)
        source.setdefault("last_reviewed_at", reviewed_at)
        source_org, _ = SourceOrganization.objects.update_or_create(name=name, defaults=source)
        sources[name] = source_org

    opportunities = [
        {
            "name": "Youth Opportunity Grant",
            "opportunity_type": Opportunity.OpportunityType.GRANT,
            "source_type": Opportunity.SourceType.FUNDER,
            "source_name": "Orange Community Foundation",
            "geography": ["Orlando", "Orange County", "Florida"],
            "focus_areas": ["youth opportunity", "technology skills", "community development"],
            "beneficiaries": ["youth", "low-income residents", "job seekers"],
            "eligibility_notes": "Demo grant for nonprofit youth opportunity programs serving Orlando residents.",
            "status": Opportunity.Status.ACTIVE,
            "priority_level": Opportunity.PriorityLevel.HIGH,
            "deadline": date(2026, 8, 15),
            "notes": "Excellent local fit for Bright Future Youth Collective-style youth opportunity work.",
        },
        {
            "name": "Workforce Development Grant",
            "opportunity_type": Opportunity.OpportunityType.GRANT,
            "source_type": Opportunity.SourceType.FUNDER,
            "source_name": "Florida Workforce Innovation Fund",
            "geography": ["Florida", "Orange County"],
            "focus_areas": ["workforce development", "career readiness", "credentials"],
            "beneficiaries": ["young adults", "job seekers", "low-income residents"],
            "eligibility_notes": "Demo grant for employer-connected training and measurable workforce outcomes.",
            "status": Opportunity.Status.ACTIVE,
            "priority_level": Opportunity.PriorityLevel.HIGH,
            "deadline": date(2026, 9, 1),
            "notes": "Strong workforce alignment with statewide eligibility.",
        },
        {
            "name": "Youth Technology Initiative",
            "opportunity_type": Opportunity.OpportunityType.CONTRACT,
            "source_type": Opportunity.SourceType.GOVERNMENT,
            "source_name": "City of Orlando Youth and Workforce Office",
            "geography": ["Orlando", "Florida"],
            "focus_areas": ["youth services", "technology training", "youth opportunity"],
            "beneficiaries": ["youth", "students", "young adults"],
            "eligibility_notes": "Demo city contract lane for youth technology workshops and service delivery.",
            "status": Opportunity.Status.UPCOMING,
            "priority_level": Opportunity.PriorityLevel.HIGH,
            "deadline": date(2026, 10, 10),
            "notes": "Upcoming public-sector opportunity tied to youth technology services.",
        },
        {
            "name": "Community Partnership Program",
            "opportunity_type": Opportunity.OpportunityType.PARTNERSHIP,
            "source_type": Opportunity.SourceType.PARTNER,
            "source_name": "Neighborhood Youth Inclusion Coalition",
            "geography": ["Orlando", "Orange County"],
            "focus_areas": ["youth opportunity", "community outreach", "device access"],
            "beneficiaries": ["families", "low-income residents", "job seekers"],
            "eligibility_notes": "Demo partnership program for referrals, outreach, and shared workshops.",
            "status": Opportunity.Status.MONITORING,
            "priority_level": Opportunity.PriorityLevel.MEDIUM,
            "deadline": date(2026, 11, 3),
            "notes": "Partnership lane to monitor while partner roles are clarified.",
        },
        {
            "name": "Capacity Building Resource Program",
            "opportunity_type": Opportunity.OpportunityType.CAPACITY_BUILDING,
            "source_type": Opportunity.SourceType.RESOURCE_PROVIDER,
            "source_name": "Florida Nonprofit Capacity Lab",
            "geography": ["Florida"],
            "focus_areas": ["capacity building", "evaluation", "fundraising"],
            "beneficiaries": ["nonprofits", "community organizations"],
            "eligibility_notes": "Demo resource program for evaluation, fundraising, and operating capacity.",
            "status": Opportunity.Status.ACTIVE,
            "priority_level": Opportunity.PriorityLevel.MEDIUM,
            "deadline": date(2026, 12, 1),
            "notes": "Useful capacity support that indirectly improves funding readiness.",
        },
        {
            "name": "Employer Mentorship Sponsorship",
            "opportunity_type": Opportunity.OpportunityType.SPONSORSHIP,
            "source_type": Opportunity.SourceType.PARTNER,
            "source_name": "Central Florida Corporate Citizenship Council",
            "geography": ["Regional", "Florida"],
            "focus_areas": ["career readiness", "mentoring", "technology careers"],
            "beneficiaries": ["young adults", "students"],
            "eligibility_notes": "Sponsorship for nonprofits connecting students and job seekers to employers.",
            "status": Opportunity.Status.MONITORING,
            "priority_level": Opportunity.PriorityLevel.MEDIUM,
            "deadline": date(2026, 7, 30),
            "notes": "Good employer engagement fit with regional rather than city-specific scope.",
        },
        {
            "name": "Civic Tech Training Fellowship",
            "opportunity_type": Opportunity.OpportunityType.TRAINING,
            "source_type": Opportunity.SourceType.RESOURCE_PROVIDER,
            "source_name": "University Of Central Florida Civic Innovation Center",
            "geography": ["Orlando", "Florida"],
            "focus_areas": ["technology training", "civic technology", "education"],
            "beneficiaries": ["students", "young adults"],
            "eligibility_notes": "Training fellowship for community organizations running civic technology programs.",
            "status": Opportunity.Status.ACTIVE,
            "priority_level": Opportunity.PriorityLevel.HIGH,
            "deadline": date(2026, 8, 28),
            "notes": "Strong local training fit with education and technology emphasis.",
        },
        {
            "name": "County Community Development Contract",
            "opportunity_type": Opportunity.OpportunityType.CONTRACT,
            "source_type": Opportunity.SourceType.GOVERNMENT,
            "source_name": "Orange Housing Stability Office",
            "geography": ["Orange County", "Florida"],
            "focus_areas": ["community development", "housing", "resident services"],
            "beneficiaries": ["low-income residents", "families"],
            "eligibility_notes": "County contract for community outreach and resident service navigation.",
            "status": Opportunity.Status.UPCOMING,
            "priority_level": Opportunity.PriorityLevel.MEDIUM,
            "deadline": date(2026, 9, 20),
            "notes": "Moderate adjacency through community development and geography.",
        },
        {
            "name": "Small Business Life Skills Grant",
            "opportunity_type": Opportunity.OpportunityType.GRANT,
            "source_type": Opportunity.SourceType.FUNDER,
            "source_name": "Orange Community Foundation",
            "geography": ["Orange County", "Florida"],
            "focus_areas": ["small business", "life skills", "economic mobility"],
            "beneficiaries": ["entrepreneurs", "adults", "low-income residents"],
            "eligibility_notes": "Grant for organizations helping small businesses adopt basic digital tools.",
            "status": Opportunity.Status.ACTIVE,
            "priority_level": Opportunity.PriorityLevel.MEDIUM,
            "deadline": date(2026, 10, 5),
            "notes": "Moderate fit through life skills and local economic mobility.",
        },
        {
            "name": "Arts Workforce Youth Residency",
            "opportunity_type": Opportunity.OpportunityType.PARTNERSHIP,
            "source_type": Opportunity.SourceType.PARTNER,
            "source_name": "Southeast Arts and Culture Trust",
            "geography": ["Regional"],
            "focus_areas": ["arts and culture", "youth development", "creative careers"],
            "beneficiaries": ["artists", "youth", "students"],
            "eligibility_notes": "Residency partnership for creative youth development programs.",
            "status": Opportunity.Status.MONITORING,
            "priority_level": Opportunity.PriorityLevel.LOW,
            "deadline": date(2027, 1, 15),
            "notes": "Some youth alignment but weaker fit with core technology and workforce model.",
        },
        {
            "name": "Regional Education Innovation Grant",
            "opportunity_type": Opportunity.OpportunityType.GRANT,
            "source_type": Opportunity.SourceType.FUNDER,
            "source_name": "Florida Workforce Innovation Fund",
            "geography": ["Regional", "Florida"],
            "focus_areas": ["education", "career readiness", "credentials"],
            "beneficiaries": ["students", "young adults"],
            "eligibility_notes": "Supports education partnerships that create credential pathways.",
            "status": Opportunity.Status.APPLIED,
            "priority_level": Opportunity.PriorityLevel.HIGH,
            "deadline": date(2026, 6, 30),
            "notes": "Application submitted for a strong education and career pathway lane.",
        },
        {
            "name": "National Health Access Training Program",
            "opportunity_type": Opportunity.OpportunityType.TRAINING,
            "source_type": Opportunity.SourceType.RESOURCE_PROVIDER,
            "source_name": "National Rural Health Collaborative",
            "geography": ["National"],
            "focus_areas": ["health", "healthcare access", "rural services"],
            "beneficiaries": ["patients", "rural residents", "health workers"],
            "eligibility_notes": "Training program for rural health outreach organizations.",
            "status": Opportunity.Status.ACTIVE,
            "priority_level": Opportunity.PriorityLevel.LOW,
            "deadline": date(2026, 9, 12),
            "notes": "Weak fit for Bright Future Youth Collective because geography and focus are outside the core profile.",
        },
        {
            "name": "Technology Equipment Donation Round",
            "opportunity_type": Opportunity.OpportunityType.RESOURCE,
            "source_type": Opportunity.SourceType.RESOURCE_PROVIDER,
            "source_name": "Florida Nonprofit Capacity Lab",
            "geography": ["Florida", "National"],
            "focus_areas": ["technology", "equipment", "youth access"],
            "beneficiaries": ["nonprofits", "low-income residents"],
            "eligibility_notes": "Equipment support for nonprofits running youth access programs.",
            "status": Opportunity.Status.WON,
            "priority_level": Opportunity.PriorityLevel.HIGH,
            "deadline": date(2026, 5, 15),
            "notes": "Won demo opportunity with clear youth access relevance.",
        },
        {
            "name": "Library Career Navigator Contract",
            "opportunity_type": Opportunity.OpportunityType.CONTRACT,
            "source_type": Opportunity.SourceType.GOVERNMENT,
            "source_name": "City of Orlando Youth and Workforce Office",
            "geography": ["Orlando", "Florida"],
            "focus_areas": ["youth opportunity", "community learning", "technology training"],
            "beneficiaries": ["adults", "families", "job seekers"],
            "eligibility_notes": "Service contract for career navigation workshops and community learning.",
            "status": Opportunity.Status.ACTIVE,
            "priority_level": Opportunity.PriorityLevel.HIGH,
            "deadline": date(2026, 8, 3),
            "notes": "Excellent local government service contract fit.",
        },
        {
            "name": "Housing Stability Outreach Mini Grant",
            "opportunity_type": Opportunity.OpportunityType.GRANT,
            "source_type": Opportunity.SourceType.GOVERNMENT,
            "source_name": "Orange Housing Stability Office",
            "geography": ["Orange County"],
            "focus_areas": ["housing", "community development", "resident services"],
            "beneficiaries": ["families", "low-income residents"],
            "eligibility_notes": "Mini grant for neighborhood outreach around housing stability programs.",
            "status": Opportunity.Status.UPCOMING,
            "priority_level": Opportunity.PriorityLevel.LOW,
            "deadline": date(2026, 11, 19),
            "notes": "Geographic fit, but weaker program alignment.",
        },
        {
            "name": "Youth Career Exploration Sponsorship",
            "opportunity_type": Opportunity.OpportunityType.SPONSORSHIP,
            "source_type": Opportunity.SourceType.PARTNER,
            "source_name": "Central Florida Corporate Citizenship Council",
            "geography": ["Orlando", "Regional"],
            "focus_areas": ["youth development", "career readiness", "mentoring"],
            "beneficiaries": ["youth", "students", "young adults"],
            "eligibility_notes": "Corporate sponsorship for youth career exploration events.",
            "status": Opportunity.Status.ACTIVE,
            "priority_level": Opportunity.PriorityLevel.HIGH,
            "deadline": date(2026, 7, 22),
            "notes": "Excellent sponsor lane for youth and employer-connected programming.",
        },
        {
            "name": "Community Arts Technology Lab",
            "opportunity_type": Opportunity.OpportunityType.CAPACITY_BUILDING,
            "source_type": Opportunity.SourceType.RESOURCE_PROVIDER,
            "source_name": "Southeast Arts and Culture Trust",
            "geography": ["Regional"],
            "focus_areas": ["arts and culture", "technology", "community development"],
            "beneficiaries": ["artists", "community organizations"],
            "eligibility_notes": "Capacity-building cohort for arts organizations using technology labs.",
            "status": Opportunity.Status.MONITORING,
            "priority_level": Opportunity.PriorityLevel.LOW,
            "deadline": date(2027, 2, 1),
            "notes": "Technology adjacency but lower direct beneficiary and program fit.",
        },
        {
            "name": "National Volunteer Tutor Network",
            "opportunity_type": Opportunity.OpportunityType.PARTNERSHIP,
            "source_type": Opportunity.SourceType.PARTNER,
            "source_name": "National Rural Health Collaborative",
            "geography": ["National"],
            "focus_areas": ["education", "volunteers", "health literacy"],
            "beneficiaries": ["rural residents", "students"],
            "eligibility_notes": "National volunteer partnership for health literacy tutoring.",
            "status": Opportunity.Status.ARCHIVED,
            "priority_level": Opportunity.PriorityLevel.LOW,
            "deadline": date(2026, 3, 31),
            "notes": "Archived weak fit retained to test status filtering and scoring spread.",
        },
        {
            "name": "Workforce Board Incumbent Worker Training",
            "opportunity_type": Opportunity.OpportunityType.TRAINING,
            "source_type": Opportunity.SourceType.GOVERNMENT,
            "source_name": "Florida Workforce Innovation Fund",
            "geography": ["Florida"],
            "focus_areas": ["workforce development", "training", "job placement"],
            "beneficiaries": ["workers", "job seekers", "adults"],
            "eligibility_notes": "Training funds for workforce providers with employer placement pathways.",
            "status": Opportunity.Status.ACTIVE,
            "priority_level": Opportunity.PriorityLevel.MEDIUM,
            "deadline": date(2026, 12, 18),
            "notes": "Strong workforce alignment, with less youth-specific emphasis.",
        },
        {
            "name": "Community Data Evaluation Support",
            "opportunity_type": Opportunity.OpportunityType.CAPACITY_BUILDING,
            "source_type": Opportunity.SourceType.RESOURCE_PROVIDER,
            "source_name": "University Of Central Florida Civic Innovation Center",
            "geography": ["Orlando", "Florida"],
            "focus_areas": ["evaluation", "data", "community development"],
            "beneficiaries": ["nonprofits", "community organizations"],
            "eligibility_notes": "Technical support for nonprofits documenting outcomes and impact.",
            "status": Opportunity.Status.ACTIVE,
            "priority_level": Opportunity.PriorityLevel.MEDIUM,
            "deadline": date(2026, 9, 25),
            "notes": "Good readiness support even though it is not a direct program opportunity.",
        },
        {
            "name": "Veterans Digital Career Transition Grant",
            "opportunity_type": Opportunity.OpportunityType.GRANT,
            "source_type": Opportunity.SourceType.FUNDER,
            "source_name": "Florida Veterans Community Fund",
            "geography": ["Florida"],
            "focus_areas": ["Veterans", "Workforce Development", "Youth Opportunity", "Mental Health"],
            "beneficiaries": ["veterans", "job seekers", "adults"],
            "eligibility_notes": "Grant for nonprofits helping veterans transition into career readiness.",
            "status": Opportunity.Status.MONITORING,
            "priority_level": Opportunity.PriorityLevel.MEDIUM,
            "deadline": date(2026, 10, 22),
            "notes": "Moderate workforce and digital fit with a more specific veteran population.",
        },
        {
            "name": "LGBTQ+ Youth Mental Health Partnership",
            "opportunity_type": Opportunity.OpportunityType.PARTNERSHIP,
            "source_type": Opportunity.SourceType.PARTNER,
            "source_name": "Rainbow Community Wellness Coalition",
            "geography": ["Orlando", "Florida"],
            "focus_areas": ["LGBTQ+", "Mental Health", "Youth Development", "Community Development"],
            "beneficiaries": ["LGBTQ+ youth", "students", "families"],
            "eligibility_notes": "Partnership for community organizations serving LGBTQ+ youth wellness and referral pathways.",
            "status": Opportunity.Status.UPCOMING,
            "priority_level": Opportunity.PriorityLevel.LOW,
            "deadline": date(2026, 11, 8),
            "notes": "Local youth adjacency, but lower direct fit with workforce and youth opportunity programming.",
        },
        {
            "name": "Inclusive Technology Access Resource Round",
            "opportunity_type": Opportunity.OpportunityType.RESOURCE,
            "source_type": Opportunity.SourceType.RESOURCE_PROVIDER,
            "source_name": "Access Forward Disability Network",
            "geography": ["Florida", "Regional"],
            "focus_areas": ["Disability", "Youth Opportunity", "Education"],
            "beneficiaries": ["disabled residents", "students", "job seekers"],
            "eligibility_notes": "Assistive technology and accessibility support for nonprofits operating digital learning programs.",
            "status": Opportunity.Status.ACTIVE,
            "priority_level": Opportunity.PriorityLevel.MEDIUM,
            "deadline": date(2026, 9, 29),
            "notes": "Strong youth opportunity relevance with a disability access lens.",
        },
        {
            "name": "Neighborhood Food Access Volunteer Program",
            "opportunity_type": Opportunity.OpportunityType.RESOURCE,
            "source_type": Opportunity.SourceType.RESOURCE_PROVIDER,
            "source_name": "Greater Orlando Food Security Alliance",
            "geography": ["Orlando", "Orange County"],
            "focus_areas": ["Food Security", "Community Development", "Volunteer Resources"],
            "beneficiaries": ["families", "low-income residents", "seniors"],
            "eligibility_notes": "Volunteer and logistics support for neighborhood food access programs.",
            "status": Opportunity.Status.MONITORING,
            "priority_level": Opportunity.PriorityLevel.LOW,
            "deadline": date(2026, 12, 6),
            "notes": "Good geography fit but weaker program alignment for the Bright Future Youth Collective demo profile.",
        },
        {
            "name": "Justice-Involved Workforce Reentry Contract",
            "opportunity_type": Opportunity.OpportunityType.CONTRACT,
            "source_type": Opportunity.SourceType.PARTNER,
            "source_name": "Second Chance Reentry Collaborative",
            "geography": ["Orange County", "Florida"],
            "focus_areas": ["Reentry / Justice-Involved", "Workforce Development", "Housing"],
            "beneficiaries": ["justice-involved residents", "job seekers", "adults"],
            "eligibility_notes": "Service contract for job readiness, life skills, and reentry navigation partners.",
            "status": Opportunity.Status.ACTIVE,
            "priority_level": Opportunity.PriorityLevel.MEDIUM,
            "deadline": date(2026, 10, 14),
            "notes": "Workforce alignment with a specialized reentry population and service model.",
        },
        {
            "name": "Senior Youth Inclusion Training",
            "opportunity_type": Opportunity.OpportunityType.TRAINING,
            "source_type": Opportunity.SourceType.RESOURCE_PROVIDER,
            "source_name": "University Of Central Florida Civic Innovation Center",
            "geography": ["Orlando", "Florida"],
            "focus_areas": ["Senior Services", "Youth Opportunity", "Education"],
            "beneficiaries": ["older adults", "seniors", "caregivers"],
            "eligibility_notes": "Training resources for organizations helping older adults build youth access skills.",
            "status": Opportunity.Status.UPCOMING,
            "priority_level": Opportunity.PriorityLevel.MEDIUM,
            "deadline": date(2026, 11, 17),
            "notes": "Local youth opportunity fit with a different beneficiary population.",
        },
        {
            "name": "Immigrant Career Pathways Partnership",
            "opportunity_type": Opportunity.OpportunityType.PARTNERSHIP,
            "source_type": Opportunity.SourceType.PARTNER,
            "source_name": "Neighborhood Youth Inclusion Coalition",
            "geography": ["Orlando", "Orange County"],
            "focus_areas": ["Immigrant / Refugee Support", "Workforce Development", "Education", "Youth Opportunity"],
            "beneficiaries": ["immigrants", "refugees", "job seekers"],
            "eligibility_notes": "Partnership for career navigation, career readiness, and referral support for newcomer communities.",
            "status": Opportunity.Status.ACTIVE,
            "priority_level": Opportunity.PriorityLevel.HIGH,
            "deadline": date(2026, 8, 19),
            "notes": "Strong local digital and workforce fit with a newcomer support emphasis.",
        },
        {
            "name": "Environmental Justice Youth Civic Lab",
            "opportunity_type": Opportunity.OpportunityType.CAPACITY_BUILDING,
            "source_type": Opportunity.SourceType.FUNDER,
            "source_name": "Everglades Environmental Justice Fund",
            "geography": ["Regional", "Florida"],
            "focus_areas": ["Environmental Justice", "Youth Development", "Community Development"],
            "beneficiaries": ["youth", "residents", "community organizations"],
            "eligibility_notes": "Capacity-building cohort for youth-led environmental justice and civic learning projects.",
            "status": Opportunity.Status.MONITORING,
            "priority_level": Opportunity.PriorityLevel.LOW,
            "deadline": date(2027, 1, 28),
            "notes": "Youth and civic adjacency with weaker direct youth development alignment.",
        },
        {
            "name": "Rural Communities Broadband Learning Grant",
            "opportunity_type": Opportunity.OpportunityType.GRANT,
            "source_type": Opportunity.SourceType.FUNDER,
            "source_name": "National Rural Health Collaborative",
            "geography": ["National"],
            "focus_areas": ["Rural Communities", "Youth Opportunity", "Healthcare", "Education"],
            "beneficiaries": ["rural residents", "patients", "students"],
            "eligibility_notes": "Grant for rural broadband adoption, telehealth learning, and community youth access.",
            "status": Opportunity.Status.ACTIVE,
            "priority_level": Opportunity.PriorityLevel.LOW,
            "deadline": date(2026, 12, 30),
            "notes": "Youth Opportunity overlap but weak geography and beneficiary fit for the Orlando demo profile.",
        },
    ]
    forecast_values = {
        "Youth Opportunity Grant": ("75000.00", Opportunity.ValueConfidence.HIGH, "Local foundation grant with a realistic mid-sized request."),
        "Workforce Development Grant": ("180000.00", Opportunity.ValueConfidence.HIGH, "Larger workforce grant with strong program fit."),
        "Youth Technology Initiative": ("240000.00", Opportunity.ValueConfidence.MEDIUM, "Potential city contract value based on service delivery scope."),
        "Community Partnership Program": ("25000.00", Opportunity.ValueConfidence.MEDIUM, "Partnership value estimated from shared programming and referrals."),
        "Capacity Building Resource Program": ("15000.00", Opportunity.ValueConfidence.HIGH, "Capacity-building support value estimated from coaching and training."),
        "Employer Mentorship Sponsorship": ("30000.00", Opportunity.ValueConfidence.MEDIUM, "Corporate sponsorship value for mentors, events, and program support."),
        "Civic Tech Training Fellowship": ("22000.00", Opportunity.ValueConfidence.MEDIUM, "Training fellowship value based on cohort support."),
        "County Community Development Contract": ("125000.00", Opportunity.ValueConfidence.MEDIUM, "County contract estimate for outreach and service navigation."),
        "Small Business Life Skills Grant": ("60000.00", Opportunity.ValueConfidence.MEDIUM, "Moderate grant estimate for life skills programming."),
        "Arts Workforce Youth Residency": ("18000.00", Opportunity.ValueConfidence.LOW, "Lower confidence because fit and scope are less direct."),
        "Regional Education Innovation Grant": ("95000.00", Opportunity.ValueConfidence.HIGH, "Submitted education grant with clearer request assumptions."),
        "National Health Access Training Program": ("12000.00", Opportunity.ValueConfidence.LOW, "Training value is modest and weaker fit for the demo profile."),
        "Technology Equipment Donation Round": ("40000.00", Opportunity.ValueConfidence.HIGH, "Won equipment value based on device and software support."),
        "Library Career Navigator Contract": ("210000.00", Opportunity.ValueConfidence.HIGH, "Local government service contract with strong career navigation fit."),
        "Housing Stability Outreach Mini Grant": ("20000.00", Opportunity.ValueConfidence.LOW, "Mini grant value for adjacent community outreach work."),
        "Youth Career Exploration Sponsorship": ("45000.00", Opportunity.ValueConfidence.HIGH, "High-priority sponsorship for youth career events."),
        "Community Arts Technology Lab": ("14000.00", Opportunity.ValueConfidence.LOW, "Lower confidence value for an adjacent capacity-building cohort."),
        "National Volunteer Tutor Network": ("5000.00", Opportunity.ValueConfidence.LOW, "Archived weak-fit volunteer partnership with limited forecast value."),
        "Workforce Board Incumbent Worker Training": ("85000.00", Opportunity.ValueConfidence.MEDIUM, "Workforce training value based on provider support assumptions."),
        "Community Data Evaluation Support": ("18000.00", Opportunity.ValueConfidence.MEDIUM, "Technical assistance value tied to evaluation support."),
        "Veterans Digital Career Transition Grant": ("70000.00", Opportunity.ValueConfidence.MEDIUM, "Moderate grant value for specialized workforce transition work."),
        "LGBTQ+ Youth Mental Health Partnership": ("22000.00", Opportunity.ValueConfidence.LOW, "Partnership value is useful but outside the core demo lane."),
        "Inclusive Technology Access Resource Round": ("35000.00", Opportunity.ValueConfidence.MEDIUM, "Resource value for accessibility and assistive technology support."),
        "Neighborhood Food Access Volunteer Program": ("8000.00", Opportunity.ValueConfidence.LOW, "Volunteer support value for adjacent wraparound services."),
        "Justice-Involved Workforce Reentry Contract": ("160000.00", Opportunity.ValueConfidence.MEDIUM, "Contract value for specialized workforce reentry services."),
        "Senior Youth Inclusion Training": ("28000.00", Opportunity.ValueConfidence.MEDIUM, "Training value for local youth inclusion programming."),
        "Immigrant Career Pathways Partnership": ("55000.00", Opportunity.ValueConfidence.MEDIUM, "Partnership value from local workforce and referral activity."),
        "Environmental Justice Youth Civic Lab": ("24000.00", Opportunity.ValueConfidence.LOW, "Capacity-building estimate for an adjacent civic learning lane."),
        "Rural Communities Broadband Learning Grant": ("50000.00", Opportunity.ValueConfidence.LOW, "Youth Opportunity overlap but lower confidence because geography is weak."),
    }
    for opportunity in opportunities:
        name = opportunity.pop("name")
        source_name = opportunity.get("source_name", "")
        opportunity["source_organization"] = sources.get(source_name)
        estimated_value, confidence, notes = forecast_values[name]
        if opportunity["opportunity_type"] in {
            Opportunity.OpportunityType.GRANT,
            Opportunity.OpportunityType.CONTRACT,
            Opportunity.OpportunityType.SPONSORSHIP,
        }:
            opportunity["funding_amount"] = estimated_value
        opportunity["estimated_value"] = estimated_value
        opportunity["value_confidence"] = confidence
        opportunity["forecast_notes"] = notes
        opportunity["source_references"] = [
            {
                "title": f"{source_name or name} opportunity summary",
                "source": "Demo opportunity inventory",
            }
        ]
        opportunity["source_urls"] = [
            opportunity["source_organization"].website
        ] if opportunity["source_organization"] and opportunity["source_organization"].website else []
        opportunity["source_notes"] = f"Reviewed deterministic opportunity record for {name}."
        opportunity["verification_status"] = Opportunity.VerificationStatus.REVIEWED
        opportunity["last_reviewed_at"] = reviewed_at
        Opportunity.objects.update_or_create(name=name, defaults=opportunity)


def _seed_document_and_evidence_data(project):
    documents = [
        {
            "title": "IRS Determination Letter",
            "document_type": DocumentVaultItem.DocumentType.IRS_DETERMINATION_LETTER,
            "status": DocumentVaultItem.Status.AVAILABLE,
            "file_reference": "vault://irs-determination-letter.pdf",
            "notes": "Current 501(c)(3) determination letter ready for grant and contract packets.",
        },
        {
            "title": "W-9",
            "document_type": DocumentVaultItem.DocumentType.W9,
            "status": DocumentVaultItem.Status.AVAILABLE,
            "file_reference": "vault://w9.pdf",
            "notes": "Signed W-9 ready for funder, sponsor, and public-sector vendor requests.",
        },
        {
            "title": "Annual Budget",
            "document_type": DocumentVaultItem.DocumentType.ANNUAL_BUDGET,
            "status": DocumentVaultItem.Status.NEEDS_UPDATE,
            "file_reference": "vault://annual-budget.xlsx",
            "notes": "Needs refresh for the current fiscal year.",
        },
        {
            "title": "Program Budget",
            "document_type": DocumentVaultItem.DocumentType.PROGRAM_BUDGET,
            "status": DocumentVaultItem.Status.AVAILABLE,
            "file_reference": "vault://program-budget.xlsx",
            "notes": "Draft program budget for life skills initiative.",
        },
        {
            "title": "Board List",
            "document_type": DocumentVaultItem.DocumentType.BOARD_LIST,
            "status": DocumentVaultItem.Status.AVAILABLE,
            "file_reference": "vault://board-list.pdf",
            "notes": "Current board roster with affiliations for credibility and governance review.",
        },
        {
            "title": "Outcome Report",
            "document_type": DocumentVaultItem.DocumentType.OUTCOME_REPORT,
            "status": DocumentVaultItem.Status.MISSING,
            "notes": "Assemble workshop completions, internship placement, and device access outcomes into a board-ready impact brief.",
        },
        {
            "title": "Insurance",
            "document_type": DocumentVaultItem.DocumentType.INSURANCE,
            "status": DocumentVaultItem.Status.NEEDS_UPDATE,
            "file_reference": "vault://insurance-certificate.pdf",
            "notes": "Certificate needs current coverage dates.",
        },
        {
            "title": "Policy Document",
            "document_type": DocumentVaultItem.DocumentType.POLICY_DOCUMENT,
            "status": DocumentVaultItem.Status.MISSING,
            "notes": "Prepare safeguarding, data privacy, procurement, and accessibility policies for public-sector contract review.",
        },
    ]
    for document in documents:
        title = document.pop("title")
        DocumentVaultItem.objects.update_or_create(project=project, title=title, defaults=document)

    evidence_items = [
        {
            "title": "Participants completing life skills workshops",
            "evidence_type": EvidenceLibraryItem.EvidenceType.OUTCOME_METRIC,
            "related_program": "Life Skills workshops",
            "metric_name": "Workshop completions",
            "metric_value": "180 participants",
            "evidence_date": date(2026, 5, 1),
            "status": EvidenceLibraryItem.Status.AVAILABLE,
            "notes": "Quarterly participation metric used in foundation reports and youth opportunity grant narratives.",
        },
        {
            "title": "Youth internship placement result",
            "evidence_type": EvidenceLibraryItem.EvidenceType.PROGRAM_RESULT,
            "related_program": "Paid technology internships",
            "metric_name": "Placement rate",
            "metric_value": "68%",
            "evidence_date": date(2026, 4, 20),
            "status": EvidenceLibraryItem.Status.AVAILABLE,
            "notes": "Career pathway result showing participants moving from training into internships or entry-level roles.",
        },
        {
            "title": "Participant impact story",
            "evidence_type": EvidenceLibraryItem.EvidenceType.IMPACT_STORY,
            "related_program": "Youth career exploration",
            "status": EvidenceLibraryItem.Status.NEEDS_UPDATE,
            "notes": "Needs permission and current quote.",
        },
        {
            "title": "Community broadband need data",
            "evidence_type": EvidenceLibraryItem.EvidenceType.COMMUNITY_NEED_DATA,
            "related_program": "Device access",
            "status": EvidenceLibraryItem.Status.AVAILABLE,
            "evidence_date": date(2026, 3, 15),
            "notes": "Local youth access data used to explain why device support and career navigation remain urgent.",
        },
        {
            "title": "Employer testimonial",
            "evidence_type": EvidenceLibraryItem.EvidenceType.TESTIMONIAL,
            "related_program": "Employer-connected workforce training",
            "status": EvidenceLibraryItem.Status.MISSING,
            "notes": "Employer testimonial needs to be requested.",
        },
        {
            "title": "Partner support letter",
            "evidence_type": EvidenceLibraryItem.EvidenceType.PARTNER_LETTER,
            "related_program": "Community partnerships",
            "status": EvidenceLibraryItem.Status.MISSING,
            "notes": "Partner letter needed for partnership and grant submissions.",
        },
        {
            "title": "Evaluation memo",
            "evidence_type": EvidenceLibraryItem.EvidenceType.EVALUATION_REPORT,
            "related_program": "Life Skills workshops",
            "status": EvidenceLibraryItem.Status.NEEDS_UPDATE,
            "notes": "Evaluation memo needs current outcomes and charts.",
        },
        {
            "title": "Local media mention",
            "evidence_type": EvidenceLibraryItem.EvidenceType.MEDIA_MENTION,
            "related_program": "Youth Inclusion",
            "status": EvidenceLibraryItem.Status.AVAILABLE,
            "evidence_date": date(2026, 2, 10),
            "notes": "Community press mention that helps validate demand and local trust for youth inclusion programming.",
        },
    ]
    for evidence in evidence_items:
        title = evidence.pop("title")
        EvidenceLibraryItem.objects.update_or_create(project=project, title=title, defaults=evidence)

    for opportunity in Opportunity.objects.all():
        ensure_opportunity_document_requirements(project, opportunity)


def _seed_celebrations(project):
    celebrations = [
        {
            "title": "Youth Opportunity Grant Awarded",
            "celebration_type": Celebration.CelebrationType.OPPORTUNITY_AWARDED,
            "description": "Bright Future Youth Collective secured support for device access and life skills workshops.",
            "impact": "The award expands access to training equipment for residents preparing for career readiness.",
        },
        {
            "title": "New Workforce Partnership",
            "celebration_type": Celebration.CelebrationType.PARTNERSHIP_FORMED,
            "description": "A regional workforce partner joined the opportunity web to strengthen employer-connected pathways.",
            "impact": "The partnership improves referral pathways, placement support, and credibility for future public-sector opportunities.",
        },
        {
            "title": "Technology Access Milestone",
            "celebration_type": Celebration.CelebrationType.IMPACT_MILESTONE,
            "description": "The program documented a new milestone in learner access to devices and mentoring.",
            "impact": "More participants can complete training activities outside the classroom and prepare for internships.",
        },
        {
            "title": "Community Health Success Story",
            "celebration_type": Celebration.CelebrationType.SUCCESS_STORY,
            "description": "Career Navigation support helped a community member connect with health and benefits resources online.",
            "impact": "The story shows how youth opportunity work can support broader household stability and access.",
        },
        {
            "title": "Youth Program Expansion",
            "celebration_type": Celebration.CelebrationType.PROGRAM_LAUNCH,
            "description": "Youth career exploration expanded into a new neighborhood-based cohort.",
            "impact": "The expansion creates more early exposure to technology careers and local mentor networks.",
        },
        {
            "title": "Strategic Introduction to City Workforce Leaders",
            "celebration_type": Celebration.CelebrationType.STRATEGIC_INTRODUCTION,
            "description": "A trusted contact introduced Bright Future Youth Collective to city workforce leaders aligned with youth technology pathways.",
            "impact": "The introduction creates a clearer path toward public-sector partnership and future service opportunities.",
        },
        {
            "title": "Community Collaboration with Youth Inclusion Partners",
            "celebration_type": Celebration.CelebrationType.COMMUNITY_COLLABORATION,
            "description": "Neighborhood partners coordinated outreach, referrals, and shared workshop planning.",
            "impact": "The collaboration strengthens trust, reach, and readiness for larger youth opportunity opportunities.",
        },
        {
            "title": "Veterans Support Initiative",
            "celebration_type": Celebration.CelebrationType.ORGANIZATION_MILESTONE,
            "description": "The organization added a targeted support track for veterans seeking life skills and employment navigation.",
            "impact": "The initiative broadens the opportunity ecosystem while keeping workforce readiness at the center.",
        },
        {
            "title": "Food Security Milestone",
            "celebration_type": Celebration.CelebrationType.COMMUNITY_ACHIEVEMENT,
            "description": "A community partner integrated food access referrals into participant support planning.",
            "impact": "Participants facing immediate household needs receive stronger wraparound support while pursuing training.",
        },
        {
            "title": "Environmental Justice Partnership",
            "celebration_type": Celebration.CelebrationType.PARTNERSHIP_FORMED,
            "description": "A local environmental justice partner joined planning conversations for youth civic technology projects.",
            "impact": "The partnership connects life skills, civic learning, and neighborhood resilience work.",
        },
    ]
    for celebration in celebrations:
        title = celebration.pop("title")
        Celebration.objects.update_or_create(
            project=project,
            title=title,
            defaults={
                **celebration,
                "organization_name": project.organization.name,
                "website": project.organization.website,
            },
        )


def _seed_relationship_data(project):
    contacts = [
        {
            "name": "Maya Thompson",
            "title": "Program Officer",
            "organization": "Orange Community Foundation",
            "contact_type": OrganizationContact.ContactType.PROGRAM_OFFICER,
            "email": "maya.thompson@example.org",
            "notes": "Primary foundation contact for youth and youth opportunity grants.",
            "relationship_strength": OrganizationContact.RelationshipStrength.ESTABLISHED,
        },
        {
            "name": "Jordan Ellis",
            "title": "Workforce Grants Manager",
            "organization": "Florida Workforce Innovation Fund",
            "contact_type": OrganizationContact.ContactType.FUNDER,
            "email": "jordan.ellis@example.Florida.gov",
            "notes": "Known contact for workforce grant and training opportunities.",
            "relationship_strength": OrganizationContact.RelationshipStrength.DEVELOPING,
        },
        {
            "name": "Priya Nair",
            "title": "Youth Workforce Representative",
            "organization": "City of Orlando Youth and Workforce Office",
            "contact_type": OrganizationContact.ContactType.GOVERNMENT_CONTACT,
            "email": "priya.nair@example.gov",
            "notes": "City contact for youth services, service contracts, and youth access programs.",
            "relationship_strength": OrganizationContact.RelationshipStrength.STRONG,
        },
        {
            "name": "Andre Lewis",
            "title": "Community Outreach Lead",
            "organization": "Neighborhood Youth Inclusion Coalition",
            "contact_type": OrganizationContact.ContactType.COMMUNITY_LEADER,
            "email": "andre.lewis@example.org",
            "notes": "Community partner contact for referrals, neighborhood outreach, and device access.",
            "relationship_strength": OrganizationContact.RelationshipStrength.STRONG,
        },
        {
            "name": "Elena Cruz",
            "title": "Corporate Citizenship Director",
            "organization": "Central Florida Corporate Citizenship Council",
            "contact_type": OrganizationContact.ContactType.CORPORATE_CONTACT,
            "email": "elena.cruz@example.com",
            "notes": "Corporate contact for sponsorships, mentors, and employer introductions.",
            "relationship_strength": OrganizationContact.RelationshipStrength.DEVELOPING,
        },
        {
            "name": "Samir Patel",
            "title": "Career Pathways Dean",
            "organization": "Orlando Community College Career Pathways",
            "contact_type": OrganizationContact.ContactType.PARTNER,
            "email": "samir.patel@example.edu",
            "notes": "Academic partner for credentials, shared training space, and referrals.",
            "relationship_strength": OrganizationContact.RelationshipStrength.ESTABLISHED,
        },
    ]
    for contact in contacts:
        name = contact.pop("name")
        organization_name = contact.get("organization", "")
        OrganizationContact.objects.update_or_create(
            project=project,
            name=name,
            organization=organization_name,
            defaults=contact,
        )

    partners = [
        {
            "organization_name": "Neighborhood Youth Inclusion Coalition",
            "partner_type": RelationshipPartnerOrganization.PartnerType.COMMUNITY_PARTNER,
            "geography": ["Orlando", "Orange County"],
            "relationship_strength": RelationshipPartnerOrganization.RelationshipStrength.STRONG,
            "website": "https://neighborhood-digital-inclusion.example.org",
            "notes": "Community partner for outreach, referrals, shared workshops, and device distribution.",
            "mission_alignment_notes": "Aligned with youth opportunity and neighborhood access goals.",
            "opportunity_notes": "Can strengthen local youth opportunity grants, referral pathways, and community implementation plans.",
            "relationship_notes": "Strong existing relationship that should anchor shared outreach and evidence collection.",
            "source_references": [{"title": "Youth Inclusion partner research", "source": "Demo research note"}],
        },
        {
            "organization_name": "City of Orlando Youth and Workforce Office",
            "partner_type": RelationshipPartnerOrganization.PartnerType.GOVERNMENT_PARTNER,
            "geography": ["Orlando", "Florida"],
            "relationship_strength": RelationshipPartnerOrganization.RelationshipStrength.ESTABLISHED,
            "website": "https://Orlando-youth-workforce.example.gov",
            "notes": "Public-sector partner for youth workforce, contracts, and city grants.",
            "mission_alignment_notes": "Aligned with youth workforce, city grants, service contracts, and youth access programs.",
            "opportunity_notes": "Can unlock local government grants, RFP visibility, and city-backed youth technology pathways.",
            "relationship_notes": "Maintain as a high-leverage relationship for public-sector pathway development.",
            "source_references": [{"title": "City workforce office relationship note", "source": "Demo research note"}],
        },
        {
            "organization_name": "Orlando Community College Career Pathways",
            "partner_type": RelationshipPartnerOrganization.PartnerType.ACADEMIC_PARTNER,
            "geography": ["Orlando", "Florida"],
            "relationship_strength": RelationshipPartnerOrganization.RelationshipStrength.ESTABLISHED,
            "website": "https://Orlando-community-college.example.edu",
            "notes": "Academic partner for credentials, career pathways, and shared training facilities.",
            "mission_alignment_notes": "Aligned with credentials, career pathways, and training access.",
            "opportunity_notes": "Can improve competitiveness for workforce grants that require education partners.",
            "relationship_notes": "Use as a named proof point for credential and referral partnerships.",
            "source_references": [{"title": "Community college pathway note", "source": "Demo research note"}],
        },
        {
            "organization_name": "Central Florida Corporate Citizenship Council",
            "partner_type": RelationshipPartnerOrganization.PartnerType.CORPORATE_PARTNER,
            "geography": ["Regional", "Florida"],
            "relationship_strength": RelationshipPartnerOrganization.RelationshipStrength.DEVELOPING,
            "website": "https://great-lakes-citizenship.example.com",
            "notes": "Corporate partner for sponsorships, mentors, mock interviews, and employer introductions.",
            "mission_alignment_notes": "Aligned with employer engagement, mentorship, and career exposure.",
            "opportunity_notes": "Can unlock sponsorships, mentors, and employer-backed workforce pathways.",
            "relationship_notes": "Develop into a stronger relationship before relying on employer placement claims.",
            "source_references": [{"title": "Corporate citizenship relationship note", "source": "Demo research note"}],
        },
        {
            "organization_name": "Florida Nonprofit Capacity Lab",
            "partner_type": RelationshipPartnerOrganization.PartnerType.SERVICE_PARTNER,
            "geography": ["Florida"],
            "relationship_strength": RelationshipPartnerOrganization.RelationshipStrength.DEVELOPING,
            "website": "https://Florida-capacity-lab.example.org",
            "notes": "Service partner for evaluation, capacity building, and fundraising readiness.",
            "mission_alignment_notes": "Aligned with evaluation capacity and readiness improvement.",
            "opportunity_notes": "Can improve document, evidence, and measurement readiness before pursuit.",
            "relationship_notes": "Use this partner to close readiness gaps before major funder outreach.",
            "source_references": [{"title": "Capacity partner readiness note", "source": "Demo research note"}],
        },
    ]
    for partner in partners:
        organization_name = partner.pop("organization_name")
        RelationshipPartnerOrganization.objects.update_or_create(
            project=project,
            organization_name=organization_name,
            defaults=partner,
        )


@transaction.atomic
def seed_missionsignal_demo(*, password=None):
    """Create or refresh the deterministic Anansi Atlas demo records."""
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
                "Close the opportunity gap by preparing young people and adults "
                "from underserved communities for career readiness."
            ),
            "organization_type": "Nonprofit",
            "city": "Orlando",
            "county": "Orange",
            "state": "Florida",
            "service_area_notes": (
                "Serves Orlando neighborhoods and nearby communities across "
                "Orange County, with priority for low-income residents."
            ),
        },
    )
    organization.users.add(user)

    project, _ = Project.objects.update_or_create(
        organization=organization,
        name="Primary Initiative",
        defaults={
            "programs": (
                "Life Skills workshops, youth career exploration, paid "
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
    _seed_document_and_evidence_data(project)
    _seed_relationship_data(project)
    _seed_celebrations(project)
    organization.refresh_from_db()
    project.refresh_from_db()
    return user, organization, project
