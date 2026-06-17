from django.contrib.auth import get_user_model
from django.db import transaction
from datetime import date

from openoutreach.core.models import Organization, Project
from openoutreach.funding.models import (
    Funder,
    GovernmentEntity,
    Opportunity,
    PartnerOrganization,
    ResourceProvider,
    SourceOrganization,
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

    source_organizations = [
        {
            "name": "Cuyahoga Community Foundation",
            "organization_type": SourceOrganization.OrganizationType.FOUNDATION,
            "website": "https://cuyahoga-community-foundation.example.org",
            "geography": ["Cleveland", "Cuyahoga County", "Ohio"],
            "notes": "Local foundation focused on youth, workforce, digital equity, and community development.",
        },
        {
            "name": "Ohio Workforce Innovation Fund",
            "organization_type": SourceOrganization.OrganizationType.WORKFORCE_BOARD,
            "website": "https://workforce-innovation.example.ohio.gov",
            "geography": ["Ohio"],
            "notes": "Statewide workforce funder for credentials, placement, and employer partnerships.",
        },
        {
            "name": "City of Cleveland Youth and Workforce Office",
            "organization_type": SourceOrganization.OrganizationType.GOVERNMENT_AGENCY,
            "website": "https://cleveland-youth-workforce.example.gov",
            "geography": ["Cleveland", "Ohio"],
            "notes": "City office managing youth services, workforce programs, contracts, and local RFPs.",
        },
        {
            "name": "Neighborhood Digital Inclusion Coalition",
            "organization_type": SourceOrganization.OrganizationType.NONPROFIT,
            "website": "https://neighborhood-digital-inclusion.example.org",
            "geography": ["Cleveland", "Cuyahoga County"],
            "notes": "Community coalition for outreach, device access, and digital equity partnerships.",
        },
        {
            "name": "Ohio Nonprofit Capacity Lab",
            "organization_type": SourceOrganization.OrganizationType.RESOURCE_PROVIDER,
            "website": "https://ohio-capacity-lab.example.org",
            "geography": ["Ohio"],
            "notes": "Capacity-building provider for evaluation, fundraising, and nonprofit operations.",
        },
        {
            "name": "Great Lakes Corporate Citizenship Council",
            "organization_type": SourceOrganization.OrganizationType.CORPORATE_PARTNER,
            "website": "https://great-lakes-citizenship.example.com",
            "geography": ["Regional", "Ohio"],
            "notes": "Corporate social impact network supporting sponsorships and volunteer engagement.",
        },
        {
            "name": "Midwest Arts and Culture Trust",
            "organization_type": SourceOrganization.OrganizationType.FOUNDATION,
            "website": "https://midwest-arts-trust.example.org",
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
            "name": "Cleveland State Civic Innovation Center",
            "organization_type": SourceOrganization.OrganizationType.UNIVERSITY,
            "website": "https://civic-innovation.example.edu",
            "geography": ["Cleveland", "Ohio"],
            "notes": "University center supporting applied research, training, and civic technology.",
        },
        {
            "name": "Cuyahoga Housing Stability Office",
            "organization_type": SourceOrganization.OrganizationType.GOVERNMENT_AGENCY,
            "website": "https://housing-stability.example.gov",
            "geography": ["Cuyahoga County", "Ohio"],
            "notes": "County agency focused on housing stability and community development.",
        },
        {
            "name": "Ohio Veterans Community Fund",
            "organization_type": SourceOrganization.OrganizationType.FOUNDATION,
            "website": "https://ohio-veterans-community.example.org",
            "geography": ["Ohio"],
            "notes": "Foundation focused on veterans, housing stability, mental health, and workforce transition.",
        },
        {
            "name": "Rainbow Community Wellness Coalition",
            "organization_type": SourceOrganization.OrganizationType.NONPROFIT,
            "website": "https://rainbow-wellness.example.org",
            "geography": ["Cleveland", "Ohio"],
            "notes": "Coalition supporting LGBTQ+ youth, mental health, and community-based wellness programs.",
        },
        {
            "name": "Access Forward Disability Network",
            "organization_type": SourceOrganization.OrganizationType.NONPROFIT,
            "website": "https://access-forward.example.org",
            "geography": ["Ohio", "Regional"],
            "notes": "Network focused on disability access, inclusive employment, and assistive technology.",
        },
        {
            "name": "Greater Cleveland Food Security Alliance",
            "organization_type": SourceOrganization.OrganizationType.NONPROFIT,
            "website": "https://cleveland-food-security.example.org",
            "geography": ["Cleveland", "Cuyahoga County"],
            "notes": "Alliance coordinating food security, nutrition, and community distribution programs.",
        },
        {
            "name": "Second Chance Reentry Collaborative",
            "organization_type": SourceOrganization.OrganizationType.NONPROFIT,
            "website": "https://second-chance-reentry.example.org",
            "geography": ["Cuyahoga County", "Ohio"],
            "notes": "Collaborative supporting reentry, justice-involved residents, workforce transition, and housing navigation.",
        },
        {
            "name": "Lake Erie Environmental Justice Fund",
            "organization_type": SourceOrganization.OrganizationType.FOUNDATION,
            "website": "https://lake-erie-ej.example.org",
            "geography": ["Regional", "Ohio"],
            "notes": "Foundation focused on environmental justice, climate resilience, and community development.",
        },
    ]
    sources = {}
    for source in source_organizations:
        name = source.pop("name")
        source_org, _ = SourceOrganization.objects.update_or_create(name=name, defaults=source)
        sources[name] = source_org

    opportunities = [
        {
            "name": "Digital Equity Grant",
            "opportunity_type": Opportunity.OpportunityType.GRANT,
            "source_type": Opportunity.SourceType.FUNDER,
            "source_name": "Cuyahoga Community Foundation",
            "geography": ["Cleveland", "Cuyahoga County", "Ohio"],
            "focus_areas": ["digital equity", "technology skills", "community development"],
            "beneficiaries": ["youth", "low-income residents", "job seekers"],
            "eligibility_notes": "Demo grant for nonprofit digital equity programs serving Cleveland residents.",
            "status": Opportunity.Status.ACTIVE,
            "priority_level": Opportunity.PriorityLevel.HIGH,
            "deadline": date(2026, 8, 15),
            "notes": "Excellent local fit for BridgeForward-style digital equity work.",
        },
        {
            "name": "Workforce Development Grant",
            "opportunity_type": Opportunity.OpportunityType.GRANT,
            "source_type": Opportunity.SourceType.FUNDER,
            "source_name": "Ohio Workforce Innovation Fund",
            "geography": ["Ohio", "Cuyahoga County"],
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
            "source_name": "City of Cleveland Youth and Workforce Office",
            "geography": ["Cleveland", "Ohio"],
            "focus_areas": ["youth services", "technology training", "digital equity"],
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
            "source_name": "Neighborhood Digital Inclusion Coalition",
            "geography": ["Cleveland", "Cuyahoga County"],
            "focus_areas": ["digital equity", "community outreach", "device access"],
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
            "source_name": "Ohio Nonprofit Capacity Lab",
            "geography": ["Ohio"],
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
            "source_name": "Great Lakes Corporate Citizenship Council",
            "geography": ["Regional", "Ohio"],
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
            "source_name": "Cleveland State Civic Innovation Center",
            "geography": ["Cleveland", "Ohio"],
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
            "source_name": "Cuyahoga Housing Stability Office",
            "geography": ["Cuyahoga County", "Ohio"],
            "focus_areas": ["community development", "housing", "resident services"],
            "beneficiaries": ["low-income residents", "families"],
            "eligibility_notes": "County contract for community outreach and resident service navigation.",
            "status": Opportunity.Status.UPCOMING,
            "priority_level": Opportunity.PriorityLevel.MEDIUM,
            "deadline": date(2026, 9, 20),
            "notes": "Moderate adjacency through community development and geography.",
        },
        {
            "name": "Small Business Digital Skills Grant",
            "opportunity_type": Opportunity.OpportunityType.GRANT,
            "source_type": Opportunity.SourceType.FUNDER,
            "source_name": "Cuyahoga Community Foundation",
            "geography": ["Cuyahoga County", "Ohio"],
            "focus_areas": ["small business", "digital skills", "economic mobility"],
            "beneficiaries": ["entrepreneurs", "adults", "low-income residents"],
            "eligibility_notes": "Grant for organizations helping small businesses adopt basic digital tools.",
            "status": Opportunity.Status.ACTIVE,
            "priority_level": Opportunity.PriorityLevel.MEDIUM,
            "deadline": date(2026, 10, 5),
            "notes": "Moderate fit through digital skills and local economic mobility.",
        },
        {
            "name": "Arts Workforce Youth Residency",
            "opportunity_type": Opportunity.OpportunityType.PARTNERSHIP,
            "source_type": Opportunity.SourceType.PARTNER,
            "source_name": "Midwest Arts and Culture Trust",
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
            "source_name": "Ohio Workforce Innovation Fund",
            "geography": ["Regional", "Ohio"],
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
            "notes": "Weak fit for BridgeForward because geography and focus are outside the core profile.",
        },
        {
            "name": "Technology Equipment Donation Round",
            "opportunity_type": Opportunity.OpportunityType.RESOURCE,
            "source_type": Opportunity.SourceType.RESOURCE_PROVIDER,
            "source_name": "Ohio Nonprofit Capacity Lab",
            "geography": ["Ohio", "National"],
            "focus_areas": ["technology", "equipment", "digital access"],
            "beneficiaries": ["nonprofits", "low-income residents"],
            "eligibility_notes": "Equipment support for nonprofits running digital access programs.",
            "status": Opportunity.Status.WON,
            "priority_level": Opportunity.PriorityLevel.HIGH,
            "deadline": date(2026, 5, 15),
            "notes": "Won demo opportunity with clear digital access relevance.",
        },
        {
            "name": "Library Digital Navigator Contract",
            "opportunity_type": Opportunity.OpportunityType.CONTRACT,
            "source_type": Opportunity.SourceType.GOVERNMENT,
            "source_name": "City of Cleveland Youth and Workforce Office",
            "geography": ["Cleveland", "Ohio"],
            "focus_areas": ["digital equity", "community learning", "technology training"],
            "beneficiaries": ["adults", "families", "job seekers"],
            "eligibility_notes": "Service contract for digital navigation workshops and community learning.",
            "status": Opportunity.Status.ACTIVE,
            "priority_level": Opportunity.PriorityLevel.HIGH,
            "deadline": date(2026, 8, 3),
            "notes": "Excellent local government service contract fit.",
        },
        {
            "name": "Housing Stability Outreach Mini Grant",
            "opportunity_type": Opportunity.OpportunityType.GRANT,
            "source_type": Opportunity.SourceType.GOVERNMENT,
            "source_name": "Cuyahoga Housing Stability Office",
            "geography": ["Cuyahoga County"],
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
            "source_name": "Great Lakes Corporate Citizenship Council",
            "geography": ["Cleveland", "Regional"],
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
            "source_name": "Midwest Arts and Culture Trust",
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
            "source_name": "Ohio Workforce Innovation Fund",
            "geography": ["Ohio"],
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
            "source_name": "Cleveland State Civic Innovation Center",
            "geography": ["Cleveland", "Ohio"],
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
            "source_name": "Ohio Veterans Community Fund",
            "geography": ["Ohio"],
            "focus_areas": ["Veterans", "Workforce Development", "Digital Equity", "Mental Health"],
            "beneficiaries": ["veterans", "job seekers", "adults"],
            "eligibility_notes": "Grant for nonprofits helping veterans transition into technology-enabled careers.",
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
            "geography": ["Cleveland", "Ohio"],
            "focus_areas": ["LGBTQ+", "Mental Health", "Youth Development", "Community Development"],
            "beneficiaries": ["LGBTQ+ youth", "students", "families"],
            "eligibility_notes": "Partnership for community organizations serving LGBTQ+ youth wellness and referral pathways.",
            "status": Opportunity.Status.UPCOMING,
            "priority_level": Opportunity.PriorityLevel.LOW,
            "deadline": date(2026, 11, 8),
            "notes": "Local youth adjacency, but lower direct fit with workforce and digital equity programming.",
        },
        {
            "name": "Inclusive Technology Access Resource Round",
            "opportunity_type": Opportunity.OpportunityType.RESOURCE,
            "source_type": Opportunity.SourceType.RESOURCE_PROVIDER,
            "source_name": "Access Forward Disability Network",
            "geography": ["Ohio", "Regional"],
            "focus_areas": ["Disability", "Digital Equity", "Education"],
            "beneficiaries": ["disabled residents", "students", "job seekers"],
            "eligibility_notes": "Assistive technology and accessibility support for nonprofits operating digital learning programs.",
            "status": Opportunity.Status.ACTIVE,
            "priority_level": Opportunity.PriorityLevel.MEDIUM,
            "deadline": date(2026, 9, 29),
            "notes": "Strong digital equity relevance with a disability access lens.",
        },
        {
            "name": "Neighborhood Food Access Volunteer Program",
            "opportunity_type": Opportunity.OpportunityType.RESOURCE,
            "source_type": Opportunity.SourceType.RESOURCE_PROVIDER,
            "source_name": "Greater Cleveland Food Security Alliance",
            "geography": ["Cleveland", "Cuyahoga County"],
            "focus_areas": ["Food Security", "Community Development", "Volunteer Resources"],
            "beneficiaries": ["families", "low-income residents", "seniors"],
            "eligibility_notes": "Volunteer and logistics support for neighborhood food access programs.",
            "status": Opportunity.Status.MONITORING,
            "priority_level": Opportunity.PriorityLevel.LOW,
            "deadline": date(2026, 12, 6),
            "notes": "Good geography fit but weaker program alignment for the BridgeForward demo profile.",
        },
        {
            "name": "Justice-Involved Workforce Reentry Contract",
            "opportunity_type": Opportunity.OpportunityType.CONTRACT,
            "source_type": Opportunity.SourceType.PARTNER,
            "source_name": "Second Chance Reentry Collaborative",
            "geography": ["Cuyahoga County", "Ohio"],
            "focus_areas": ["Reentry / Justice-Involved", "Workforce Development", "Housing"],
            "beneficiaries": ["justice-involved residents", "job seekers", "adults"],
            "eligibility_notes": "Service contract for job readiness, digital skills, and reentry navigation partners.",
            "status": Opportunity.Status.ACTIVE,
            "priority_level": Opportunity.PriorityLevel.MEDIUM,
            "deadline": date(2026, 10, 14),
            "notes": "Workforce alignment with a specialized reentry population and service model.",
        },
        {
            "name": "Senior Digital Inclusion Training",
            "opportunity_type": Opportunity.OpportunityType.TRAINING,
            "source_type": Opportunity.SourceType.RESOURCE_PROVIDER,
            "source_name": "Cleveland State Civic Innovation Center",
            "geography": ["Cleveland", "Ohio"],
            "focus_areas": ["Senior Services", "Digital Equity", "Education"],
            "beneficiaries": ["older adults", "seniors", "caregivers"],
            "eligibility_notes": "Training resources for organizations helping older adults build digital access skills.",
            "status": Opportunity.Status.UPCOMING,
            "priority_level": Opportunity.PriorityLevel.MEDIUM,
            "deadline": date(2026, 11, 17),
            "notes": "Local digital equity fit with a different beneficiary population.",
        },
        {
            "name": "Immigrant Career Pathways Partnership",
            "opportunity_type": Opportunity.OpportunityType.PARTNERSHIP,
            "source_type": Opportunity.SourceType.PARTNER,
            "source_name": "Neighborhood Digital Inclusion Coalition",
            "geography": ["Cleveland", "Cuyahoga County"],
            "focus_areas": ["Immigrant / Refugee Support", "Workforce Development", "Education", "Digital Equity"],
            "beneficiaries": ["immigrants", "refugees", "job seekers"],
            "eligibility_notes": "Partnership for digital navigation, career readiness, and referral support for newcomer communities.",
            "status": Opportunity.Status.ACTIVE,
            "priority_level": Opportunity.PriorityLevel.HIGH,
            "deadline": date(2026, 8, 19),
            "notes": "Strong local digital and workforce fit with a newcomer support emphasis.",
        },
        {
            "name": "Environmental Justice Youth Civic Lab",
            "opportunity_type": Opportunity.OpportunityType.CAPACITY_BUILDING,
            "source_type": Opportunity.SourceType.FUNDER,
            "source_name": "Lake Erie Environmental Justice Fund",
            "geography": ["Regional", "Ohio"],
            "focus_areas": ["Environmental Justice", "Youth Development", "Community Development"],
            "beneficiaries": ["youth", "residents", "community organizations"],
            "eligibility_notes": "Capacity-building cohort for youth-led environmental justice and civic learning projects.",
            "status": Opportunity.Status.MONITORING,
            "priority_level": Opportunity.PriorityLevel.LOW,
            "deadline": date(2027, 1, 28),
            "notes": "Youth and civic adjacency with weaker direct digital workforce alignment.",
        },
        {
            "name": "Rural Communities Broadband Learning Grant",
            "opportunity_type": Opportunity.OpportunityType.GRANT,
            "source_type": Opportunity.SourceType.FUNDER,
            "source_name": "National Rural Health Collaborative",
            "geography": ["National"],
            "focus_areas": ["Rural Communities", "Digital Equity", "Healthcare", "Education"],
            "beneficiaries": ["rural residents", "patients", "students"],
            "eligibility_notes": "Grant for rural broadband adoption, telehealth learning, and community digital access.",
            "status": Opportunity.Status.ACTIVE,
            "priority_level": Opportunity.PriorityLevel.LOW,
            "deadline": date(2026, 12, 30),
            "notes": "Digital equity overlap but weak geography and beneficiary fit for the Cleveland demo profile.",
        },
    ]
    for opportunity in opportunities:
        name = opportunity.pop("name")
        source_name = opportunity.get("source_name", "")
        opportunity["source_organization"] = sources.get(source_name)
        Opportunity.objects.update_or_create(name=name, defaults=opportunity)


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
            "organization_type": "Nonprofit",
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
