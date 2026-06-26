"""
Anansi Atlas — Empowered Girls Inc. Data Seeder
Run from the project root:  .venv/bin/python seed_egi.py

What this does:
  1. Updates the organization to Empowered Girls Inc. (Orlando, FL)
  2. Replaces all demo funders / opportunities / partners / resources / gov entities
     with research-based real-world matches for EGI's mission and geography
  3. Seeds a pilot profile for the live Opportunity Web demo
"""

import os
import sys
import django
from datetime import date, timedelta

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "openoutreach.settings")
django.setup()

from django.utils import timezone
from django.db import transaction

from openoutreach.core.models import Organization, Project
from openoutreach.funding.models import (
    DocumentVaultItem,
    EvidenceLibraryItem,
    Funder,
    GovernmentEntity,
    Opportunity,
    PartnerOrganization as FundingPartnerOrg,
    ResourceProvider,
    SourceOrganization,
)
from openoutreach.signals.models import (
    Celebration,
    OrganizationContact,
    PartnerOrganization as RelPartnerOrg,
    PilotProfile,
)

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def days(n):
    return date.today() + timedelta(days=n)

def now():
    return timezone.now()

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

with transaction.atomic():

    # ── 1. Wipe demo data ──────────────────────────────────────────────────
    print("Clearing demo data…")
    Opportunity.objects.all().delete()
    FundingPartnerOrg.objects.all().delete()
    Funder.objects.all().delete()
    ResourceProvider.objects.all().delete()
    GovernmentEntity.objects.all().delete()
    SourceOrganization.objects.all().delete()
    RelPartnerOrg.objects.all().delete()
    OrganizationContact.objects.all().delete()
    Celebration.objects.all().delete()
    DocumentVaultItem.objects.all().delete()
    EvidenceLibraryItem.objects.all().delete()
    PilotProfile.objects.all().delete()

    # ── 2. Update organization profile ────────────────────────────────────
    print("Updating organization to Empowered Girls Inc…")
    org = Organization.objects.first()
    if not org:
        org = Organization()
    org.name = "Empowered Girls Inc."
    org.website = "https://www.empoweredgirlsinc.org"
    org.mission = (
        "Empowering girls ages 9-18 to grow into confident, capable women "
        "through life skills, mentorship, and programs that help them overcome "
        "barriers and achieve success. POWER: Persevere. Overcome. Win. Excel. Reform."
    )
    org.organization_summary = (
        "Empowered Girls Inc. (EGI) is a 501(c)(3) nonprofit based in Orlando, Florida. "
        "EGI serves girls ages 9-18 through structured programs in life skills, career "
        "exploration, health & wellness, education support, and community service. "
        "In 2025, EGI directly impacted 43+ girls, awarded $11,000+ in participant "
        "scholarships, and reached 5,000 families through community service initiatives. "
        "EGI's POWER framework (Persevere, Overcome, Win, Excel, Reform) anchors all "
        "programming. Vision: a strong network of girls who embrace their uniqueness "
        "and feel empowered to lead successful, productive lives."
    )
    org.organization_type = "Nonprofit"
    org.legal_structure = "501(c)(3)"
    org.nonprofit_status = "501(c)(3)"
    org.city = "Orlando"
    org.state = "Florida"
    org.headquarters_location = "Orlando, FL (P.O. Box 681102, Orlando, FL 32868)"
    org.service_geographies = ["Orlando", "Orange County", "Central Florida", "Florida"]
    org.focus_areas = [
        "girls empowerment",
        "youth development",
        "life skills",
        "mentorship",
        "career readiness",
        "health and wellness",
        "education support",
        "community service",
        "gender equity",
    ]
    org.beneficiaries = [
        "girls ages 9-18",
        "young women",
        "underserved youth",
        "families",
    ]
    org.capabilities = [
        "youth program delivery",
        "mentorship coordination",
        "life skills curriculum (POWER framework)",
        "community events and gala coordination",
        "scholarship distribution",
        "community service projects",
        "social media and community outreach",
    ]
    org.outcomes_and_impact = [
        "43+ girls directly impacted in 2025",
        "$11,000+ in scholarships and awards to participants",
        "5,000 families reached through community service",
        "Annual EGI Award Gala celebrating participant achievements",
        "Active alumni and mentor network",
    ]
    org.budget_range = "under_250k"
    org.analysis_status = "ready"
    org.save()

    # ── 3. Update project ──────────────────────────────────────────────────
    project = Project.objects.filter(organization=org).first()
    if not project:
        project = Project(organization=org)
    project.name = "Empowered Girls Inc. — Opportunity Web"
    project.organization = org
    project.programs = (
        "Life Skills · Career Development · Health & Wellness · "
        "Education Support · Community Service"
    )
    project.program_summaries = [
        {"name": "Life Skills", "description": "Core POWER framework curriculum for girls ages 9-18."},
        {"name": "Career Development", "description": "Career exploration, professional skills, and mentorship."},
        {"name": "Health & Wellness", "description": "Physical and mental wellness programming for girls."},
        {"name": "Education Support", "description": "Academic guidance and scholarship awards."},
        {"name": "Community Service", "description": "Service projects reaching thousands of families."},
    ]
    project.save()
    print(f"  Org: {org.name} | Project: {project.name}")

    # ── 4. Source Organizations ────────────────────────────────────────────
    print("Seeding source organizations…")
    src_orgs = {}
    src_map = [
        ("Community Foundation of Central Florida", "foundation", "https://www.cffcfl.org"),
        ("Dr. Phillips Charities", "foundation", "https://www.drphillipscharities.org"),
        ("Walt Disney World Community Fund", "corporate_partner", "https://impact.disney.com"),
        ("Truist Foundation", "corporate_partner", "https://www.truist.com/purpose/truist-foundation"),
        ("Jessie Ball duPont Fund", "foundation", "https://www.dupontfund.org"),
        ("U.S. Dept. of Justice — OJJDP", "government_agency", "https://ojjdp.gov"),
        ("HHS / Administration for Children & Families", "government_agency", "https://www.acf.hhs.gov"),
        ("Bank of America Charitable Foundation", "corporate_partner", "https://about.bankofamerica.com"),
        ("Orange County Government", "government_agency", "https://www.ocfl.net"),
        ("City of Orlando", "government_agency", "https://www.orlando.gov"),
        ("Florida Department of Education", "government_agency", "https://www.fldoe.org"),
        ("Florida Dept. of Children & Families", "government_agency", "https://www.myflfamilies.com"),
        ("AmeriCorps / CNCS", "government_agency", "https://www.americorps.gov"),
        ("Girls Inc. National", "nonprofit", "https://www.girlsinc.org"),
        ("United Arts of Central Florida", "nonprofit", "https://unitedarts.cc"),
        ("Walmart Foundation", "corporate_partner", "https://walmart.org"),
    ]
    for name, org_type, website in src_map:
        s = SourceOrganization.objects.create(
            name=name, organization_type=org_type, website=website,
            active=True, last_reviewed_at=now()
        )
        src_orgs[name] = s
        print(f"  SourceOrg: {name}")

    # ── 5. Funders ────────────────────────────────────────────────────────
    print("Seeding funders…")
    funders_data = [
        {
            "name": "Community Foundation of Central Florida",
            "funder_type": Funder.FunderType.COMMUNITY_FOUNDATION,
            "geography": ["Orlando", "Orange County", "Central Florida"],
            "focus_areas": ["youth development", "girls empowerment", "education", "community programs"],
            "beneficiaries": ["youth", "girls", "underserved families"],
            "eligibility_notes": (
                "Supports 501(c)(3) organizations serving Central Florida. "
                "Competitive grant cycles in spring and fall. Youth development "
                "and girls programming are priority areas."
            ),
            "website": "https://www.cffcfl.org",
            "notes": "Primary community foundation for Orlando-area nonprofits. High alignment with EGI.",
            "intelligence_status": Funder.IntelligenceStatus.ACTIVE,
            "verification_status": Funder.VerificationStatus.REVIEWED,
        },
        {
            "name": "Dr. Phillips Charities",
            "funder_type": Funder.FunderType.FAMILY_FOUNDATION,
            "geography": ["Orlando", "Orange County"],
            "focus_areas": ["arts", "education", "human services", "health", "youth"],
            "beneficiaries": ["youth", "families", "low-income residents", "Orlando community"],
            "eligibility_notes": (
                "Orlando-based family foundation. Grants to nonprofits benefiting Orange County "
                "residents. Prefers established organizations with demonstrated community impact."
            ),
            "website": "https://www.drphillipscharities.org",
            "notes": "One of the largest Orlando-area family foundations. Strong fit for EGI's local youth impact.",
            "intelligence_status": Funder.IntelligenceStatus.ACTIVE,
            "verification_status": Funder.VerificationStatus.REVIEWED,
        },
        {
            "name": "Walt Disney World Community Fund",
            "funder_type": Funder.FunderType.CORPORATE_FOUNDATION,
            "geography": ["Orlando", "Central Florida"],
            "focus_areas": ["youth development", "education", "empowerment"],
            "beneficiaries": ["youth", "children", "underserved communities"],
            "eligibility_notes": (
                "Disney supports youth-focused nonprofits in Central Florida with grants and "
                "volunteer partnerships. Focus on imagination, learning, and youth empowerment."
            ),
            "website": "https://impact.disney.com",
            "notes": "Corporate grant + VoluntEARS program. Strong match for EGI's community events and mentorship.",
            "intelligence_status": Funder.IntelligenceStatus.ACTIVE,
            "verification_status": Funder.VerificationStatus.REVIEWED,
        },
        {
            "name": "Truist Foundation (Florida)",
            "funder_type": Funder.FunderType.CORPORATE_FOUNDATION,
            "geography": ["Florida", "Southeast", "National"],
            "focus_areas": ["career readiness", "economic mobility", "youth development", "mentorship"],
            "beneficiaries": ["youth", "young adults", "underserved communities"],
            "eligibility_notes": (
                "Truist Foundation funds programs that build career pathways and economic mobility "
                "for youth. Strong alignment with EGI's career readiness and life skills programs."
            ),
            "website": "https://www.truist.com/purpose/truist-foundation",
            "notes": "National corporate foundation with Florida presence. Career readiness is the strongest hook.",
            "intelligence_status": Funder.IntelligenceStatus.ACTIVE,
            "verification_status": Funder.VerificationStatus.REVIEWED,
        },
        {
            "name": "Jessie Ball duPont Fund",
            "funder_type": Funder.FunderType.FAMILY_FOUNDATION,
            "geography": ["Florida", "Virginia", "Delaware", "Southeast"],
            "focus_areas": ["human services", "education", "community development", "youth"],
            "beneficiaries": ["underserved communities", "youth", "families"],
            "eligibility_notes": (
                "Florida-rooted foundation funding established nonprofits in human services, "
                "education, and community programs. Must have prior relationship with the Fund."
            ),
            "website": "https://www.dupontfund.org",
            "notes": "Florida legacy foundation. EGI's 2025 impact data strengthens a future application.",
            "intelligence_status": Funder.IntelligenceStatus.MONITORING,
            "verification_status": Funder.VerificationStatus.REVIEWED,
        },
        {
            "name": "U.S. Dept. of Justice — OJJDP",
            "funder_type": Funder.FunderType.FEDERAL_GOVERNMENT,
            "geography": ["National", "Florida"],
            "focus_areas": ["juvenile justice", "youth development", "girls programs", "mentorship", "prevention"],
            "beneficiaries": ["at-risk youth", "girls", "young women"],
            "eligibility_notes": (
                "OJJDP funds prevention, intervention, and girls-specific programming nationally. "
                "Several grant categories directly serve youth empowerment and gender-responsive programs."
            ),
            "website": "https://ojjdp.gov",
            "notes": "Federal funder with multiple girls-specific programs. EGI's model is directly aligned.",
            "intelligence_status": Funder.IntelligenceStatus.PROSPECT,
            "verification_status": Funder.VerificationStatus.REVIEWED,
        },
        {
            "name": "HHS / Administration for Children & Families",
            "funder_type": Funder.FunderType.FEDERAL_GOVERNMENT,
            "geography": ["National", "Florida"],
            "focus_areas": ["youth development", "mentorship", "health and wellness", "family support"],
            "beneficiaries": ["youth", "girls", "families", "at-risk youth"],
            "eligibility_notes": (
                "ACF funds Mentoring Children of Promise, Positive Youth Development, and related "
                "programs. Florida Region IV office serves as key contact."
            ),
            "website": "https://www.acf.hhs.gov",
            "notes": "ACF Mentoring programs are a strong match. Track CFDA 93.599 and youth mentoring NOFAs.",
            "intelligence_status": Funder.IntelligenceStatus.PROSPECT,
            "verification_status": Funder.VerificationStatus.REVIEWED,
        },
        {
            "name": "Bank of America Charitable Foundation (Florida)",
            "funder_type": Funder.FunderType.CORPORATE_FOUNDATION,
            "geography": ["Florida", "National"],
            "focus_areas": ["economic mobility", "workforce development", "youth empowerment", "education"],
            "beneficiaries": ["youth", "women", "low-income individuals"],
            "eligibility_notes": (
                "Bank of America funds workforce readiness, financial literacy, and youth empowerment "
                "programs in local markets. Relationship with local branch manager can open doors."
            ),
            "website": "https://about.bankofamerica.com/en/making-an-impact/charitable-foundation-funding",
            "notes": "Strong fit for EGI's career readiness and economic empowerment components.",
            "intelligence_status": Funder.IntelligenceStatus.PROSPECT,
            "verification_status": Funder.VerificationStatus.NEEDS_REVIEW,
        },
    ]
    for d in funders_data:
        Funder.objects.create(**d, last_reviewed_at=now())
        print(f"  Funder: {d['name']}")

    # ── 6. Opportunities ──────────────────────────────────────────────────
    print("Seeding opportunities…")
    opps_data = [
        {
            "name": "Youth Development General Grant",
            "opportunity_type": Opportunity.OpportunityType.GRANT,
            "source_organization": src_orgs["Community Foundation of Central Florida"],
            "source_type": Opportunity.SourceType.FUNDER,
            "source_name": "Community Foundation of Central Florida",
            "geography": ["Orlando", "Orange County", "Central Florida"],
            "focus_areas": ["youth development", "girls programs", "life skills"],
            "beneficiaries": ["youth", "girls", "underserved families"],
            "eligibility_notes": "501(c)(3) organizations serving Central Florida youth. Submit LOI first.",
            "funding_amount": "5000.00",
            "status": Opportunity.Status.ACTIVE,
            "deadline": days(62),
            "priority_level": Opportunity.PriorityLevel.HIGH,
            "lifecycle_status": Opportunity.LifecycleStatus.REVIEWING,
            "notes": "High alignment with EGI's mission and geography. Spring cycle.",
        },
        {
            "name": "Girls & Women Empowerment Initiative",
            "opportunity_type": Opportunity.OpportunityType.GRANT,
            "source_organization": src_orgs["Dr. Phillips Charities"],
            "source_type": Opportunity.SourceType.FUNDER,
            "source_name": "Dr. Phillips Charities",
            "geography": ["Orlando", "Orange County"],
            "focus_areas": ["girls empowerment", "education", "youth development"],
            "beneficiaries": ["girls", "young women", "Orlando youth"],
            "eligibility_notes": "Orlando-area nonprofits with demonstrated community impact.",
            "funding_amount": "10000.00",
            "status": Opportunity.Status.ACTIVE,
            "deadline": days(45),
            "priority_level": Opportunity.PriorityLevel.HIGH,
            "lifecycle_status": Opportunity.LifecycleStatus.REVIEWING,
            "notes": "Top priority. Use 2025 impact data (43+ girls, $11K+ in awards) prominently.",
        },
        {
            "name": "Youth Empowerment Program Grant — OJJDP",
            "opportunity_type": Opportunity.OpportunityType.GRANT,
            "source_organization": src_orgs["U.S. Dept. of Justice — OJJDP"],
            "source_type": Opportunity.SourceType.GOVERNMENT,
            "source_name": "U.S. Dept. of Justice — OJJDP",
            "geography": ["National", "Florida"],
            "focus_areas": ["girls programs", "youth development", "prevention", "mentorship"],
            "beneficiaries": ["at-risk girls", "youth ages 9-18"],
            "eligibility_notes": "501(c)(3) nonprofits with gender-responsive youth programming. Requires evaluation plan.",
            "funding_amount": "150000.00",
            "status": Opportunity.Status.UPCOMING,
            "deadline": days(90),
            "priority_level": Opportunity.PriorityLevel.HIGH,
            "lifecycle_status": Opportunity.LifecycleStatus.DISCOVERED,
            "notes": "Federal competitive grant. Requires partner letters and data evaluation component.",
        },
        {
            "name": "Mentoring Children of Promise (ACF / HHS)",
            "opportunity_type": Opportunity.OpportunityType.GRANT,
            "source_organization": src_orgs["HHS / Administration for Children & Families"],
            "source_type": Opportunity.SourceType.GOVERNMENT,
            "source_name": "HHS / Administration for Children & Families",
            "geography": ["National"],
            "focus_areas": ["mentorship", "youth development", "girls programs", "health and wellness"],
            "beneficiaries": ["at-risk youth", "girls"],
            "eligibility_notes": "501(c)(3) organizations with mentoring programs. Prior mentoring track record required.",
            "funding_amount": "75000.00",
            "status": Opportunity.Status.MONITORING,
            "deadline": days(120),
            "priority_level": Opportunity.PriorityLevel.HIGH,
            "lifecycle_status": Opportunity.LifecycleStatus.DISCOVERED,
            "notes": "CFDA 93.599. EGI's mentorship model directly aligned. Document mentor-mentee match ratios.",
        },
        {
            "name": "AmeriCorps Volunteer Generation Fund",
            "opportunity_type": Opportunity.OpportunityType.GRANT,
            "source_organization": src_orgs["AmeriCorps / CNCS"],
            "source_type": Opportunity.SourceType.GOVERNMENT,
            "source_name": "AmeriCorps / CNCS",
            "geography": ["National", "Florida"],
            "focus_areas": ["community service", "volunteer engagement", "youth programs"],
            "beneficiaries": ["youth", "communities", "volunteers"],
            "eligibility_notes": "Organizations that recruit and manage volunteers for community programs.",
            "funding_amount": "50000.00",
            "status": Opportunity.Status.MONITORING,
            "deadline": days(135),
            "priority_level": Opportunity.PriorityLevel.MEDIUM,
            "lifecycle_status": Opportunity.LifecycleStatus.DISCOVERED,
            "notes": "EGI's community service component is a strong fit. Could fund volunteer coordination.",
        },
        {
            "name": "Walmart Foundation Community Giving (Florida)",
            "opportunity_type": Opportunity.OpportunityType.GRANT,
            "source_organization": src_orgs["Walmart Foundation"],
            "source_type": Opportunity.SourceType.FUNDER,
            "source_name": "Walmart Foundation",
            "geography": ["Florida"],
            "focus_areas": ["youth development", "education", "community programs"],
            "beneficiaries": ["youth", "families", "underserved communities"],
            "eligibility_notes": "Apply through local Walmart store manager or community giving portal. Low barrier.",
            "funding_amount": "5000.00",
            "status": Opportunity.Status.ACTIVE,
            "deadline": days(30),
            "priority_level": Opportunity.PriorityLevel.MEDIUM,
            "lifecycle_status": Opportunity.LifecycleStatus.DISCOVERED,
            "notes": "Accessible local giving. Good for program supplies and event costs.",
        },
        {
            "name": "Florida Dept. of Education — Youth Development Programs",
            "opportunity_type": Opportunity.OpportunityType.GRANT,
            "source_organization": src_orgs["Florida Department of Education"],
            "source_type": Opportunity.SourceType.GOVERNMENT,
            "source_name": "Florida Department of Education",
            "geography": ["Florida"],
            "focus_areas": ["education support", "youth development", "after-school programs"],
            "beneficiaries": ["K-12 students", "girls", "youth"],
            "eligibility_notes": "Florida 501(c)(3) organizations providing supplemental education or after-school programming.",
            "funding_amount": None,
            "status": Opportunity.Status.MONITORING,
            "deadline": days(105),
            "priority_level": Opportunity.PriorityLevel.MEDIUM,
            "lifecycle_status": Opportunity.LifecycleStatus.DISCOVERED,
            "notes": "Multiple grant lanes through FLDOE. EGI's academic support focus creates alignment.",
        },
        {
            "name": "Girls Inc. National Affiliate Relationship",
            "opportunity_type": Opportunity.OpportunityType.PARTNERSHIP,
            "source_organization": src_orgs["Girls Inc. National"],
            "source_type": Opportunity.SourceType.PARTNER,
            "source_name": "Girls Inc. National",
            "geography": ["National"],
            "focus_areas": ["girls empowerment", "programming", "network access"],
            "beneficiaries": ["girls", "young women"],
            "eligibility_notes": "Organizations running girls-specific programming. Affiliation provides curriculum access and national funder introductions.",
            "funding_amount": None,
            "status": Opportunity.Status.MONITORING,
            "deadline": days(180),
            "priority_level": Opportunity.PriorityLevel.HIGH,
            "lifecycle_status": Opportunity.LifecycleStatus.DISCOVERED,
            "notes": "Strategic priority. Girls Inc. affiliation opens national funder doors and proven curriculum.",
        },
        {
            "name": "Disney VoluntEARS + Community Partnership",
            "opportunity_type": Opportunity.OpportunityType.PARTNERSHIP,
            "source_organization": src_orgs["Walt Disney World Community Fund"],
            "source_type": Opportunity.SourceType.PARTNER,
            "source_name": "Walt Disney World Community Fund",
            "geography": ["Orlando"],
            "focus_areas": ["youth programs", "mentorship", "community events"],
            "beneficiaries": ["youth", "girls"],
            "eligibility_notes": "Orlando nonprofits serving youth. Disney provides volunteers, event space, and potential grants.",
            "funding_amount": None,
            "status": Opportunity.Status.ACTIVE,
            "deadline": days(60),
            "priority_level": Opportunity.PriorityLevel.HIGH,
            "lifecycle_status": Opportunity.LifecycleStatus.REVIEWING,
            "notes": "VoluntEARS program aligns well with EGI's mentorship model and Award Gala events.",
        },
        {
            "name": "Orange County Schools — School Partnership MOA",
            "opportunity_type": Opportunity.OpportunityType.PARTNERSHIP,
            "source_organization": src_orgs["Orange County Government"],
            "source_type": Opportunity.SourceType.GOVERNMENT,
            "source_name": "Orange County Government",
            "geography": ["Orange County", "Orlando"],
            "focus_areas": ["education", "girls programs", "after-school", "life skills"],
            "beneficiaries": ["K-12 students", "girls ages 9-18"],
            "eligibility_notes": "Organizations with school-based or school-connected programs. Requires MOA with district.",
            "funding_amount": None,
            "status": Opportunity.Status.ACTIVE,
            "deadline": days(55),
            "priority_level": Opportunity.PriorityLevel.HIGH,
            "lifecycle_status": Opportunity.LifecycleStatus.REVIEWING,
            "notes": "School access MOU could significantly expand enrollment pipeline for EGI programs.",
        },
        {
            "name": "City of Orlando Youth Programs RFP",
            "opportunity_type": Opportunity.OpportunityType.CONTRACT,
            "source_organization": src_orgs["City of Orlando"],
            "source_type": Opportunity.SourceType.GOVERNMENT,
            "source_name": "City of Orlando",
            "geography": ["Orlando"],
            "focus_areas": ["youth development", "girls programs", "community programs"],
            "beneficiaries": ["Orlando youth", "girls", "underserved communities"],
            "eligibility_notes": "501(c)(3) organizations with youth programming in Orlando city limits.",
            "funding_amount": "25000.00",
            "status": Opportunity.Status.UPCOMING,
            "deadline": days(75),
            "priority_level": Opportunity.PriorityLevel.HIGH,
            "lifecycle_status": Opportunity.LifecycleStatus.DISCOVERED,
            "notes": "City youth services contract. Annual cycle. EGI's Orlando location and 2025 impact metrics create strong eligibility.",
        },
        {
            "name": "Orange County Community Services — Youth Initiative",
            "opportunity_type": Opportunity.OpportunityType.CONTRACT,
            "source_organization": src_orgs["Orange County Government"],
            "source_type": Opportunity.SourceType.GOVERNMENT,
            "source_name": "Orange County Government",
            "geography": ["Orange County"],
            "focus_areas": ["youth development", "community programs", "girls", "prevention"],
            "beneficiaries": ["at-risk youth", "girls", "families"],
            "eligibility_notes": "Orange County 501(c)(3) organizations with documented community impact.",
            "funding_amount": "15000.00",
            "status": Opportunity.Status.UPCOMING,
            "deadline": days(88),
            "priority_level": Opportunity.PriorityLevel.MEDIUM,
            "lifecycle_status": Opportunity.LifecycleStatus.DISCOVERED,
            "notes": "County-level youth contract. Requires prior year audit. Ensure financial documents are current.",
        },
        {
            "name": "Capacity Building Initiative — CFCF",
            "opportunity_type": Opportunity.OpportunityType.CAPACITY_BUILDING,
            "source_organization": src_orgs["Community Foundation of Central Florida"],
            "source_type": Opportunity.SourceType.FUNDER,
            "source_name": "Community Foundation of Central Florida",
            "geography": ["Central Florida"],
            "focus_areas": ["organizational capacity", "nonprofit management", "strategic planning"],
            "beneficiaries": ["small nonprofits"],
            "eligibility_notes": "Small nonprofits under $500K budget in Central Florida.",
            "funding_amount": "8000.00",
            "status": Opportunity.Status.ACTIVE,
            "deadline": days(50),
            "priority_level": Opportunity.PriorityLevel.MEDIUM,
            "lifecycle_status": Opportunity.LifecycleStatus.DISCOVERED,
            "notes": "EGI is within budget threshold. Capacity support could strengthen grant infrastructure and board.",
        },
        {
            "name": "Truist Foundation — Career Pathways Initiative",
            "opportunity_type": Opportunity.OpportunityType.CAPACITY_BUILDING,
            "source_organization": src_orgs["Truist Foundation"],
            "source_type": Opportunity.SourceType.FUNDER,
            "source_name": "Truist Foundation",
            "geography": ["Florida", "Southeast"],
            "focus_areas": ["career readiness", "economic mobility", "youth workforce"],
            "beneficiaries": ["youth", "young adults", "underserved communities"],
            "eligibility_notes": "Organizations with career readiness programming. Measurable economic mobility outcomes required.",
            "funding_amount": "20000.00",
            "status": Opportunity.Status.MONITORING,
            "deadline": days(110),
            "priority_level": Opportunity.PriorityLevel.MEDIUM,
            "lifecycle_status": Opportunity.LifecycleStatus.DISCOVERED,
            "notes": "Strengthen participant employment/education pathway outcome data before applying.",
        },
        {
            "name": "EGI Award Gala — Corporate Sponsor Packages",
            "opportunity_type": Opportunity.OpportunityType.SPONSORSHIP,
            "source_organization": src_orgs["Walt Disney World Community Fund"],
            "source_type": Opportunity.SourceType.PARTNER,
            "source_name": "Walt Disney World Community Fund",
            "geography": ["Orlando"],
            "focus_areas": ["event sponsorship", "brand partnership", "community recognition"],
            "beneficiaries": ["girls", "EGI participants"],
            "eligibility_notes": "Gold/Silver/Bronze sponsor tiers. Sponsor recognition and employee engagement.",
            "funding_amount": "5000.00",
            "status": Opportunity.Status.ACTIVE,
            "deadline": days(40),
            "priority_level": Opportunity.PriorityLevel.HIGH,
            "lifecycle_status": Opportunity.LifecycleStatus.PURSUING,
            "notes": "Annual gala sponsorship is an immediate revenue opportunity. Build pipeline of 5-10 corporate prospects.",
        },
        {
            "name": "United Arts — Youth Programming Grant",
            "opportunity_type": Opportunity.OpportunityType.GRANT,
            "source_organization": src_orgs["United Arts of Central Florida"],
            "source_type": Opportunity.SourceType.FUNDER,
            "source_name": "United Arts of Central Florida",
            "geography": ["Orange County", "Central Florida"],
            "focus_areas": ["arts", "youth programs", "community"],
            "beneficiaries": ["youth", "girls", "underserved communities"],
            "eligibility_notes": "Orange County 501(c)(3)s with arts-integrated programming. Grants up to $5,000.",
            "funding_amount": "3000.00",
            "status": Opportunity.Status.ACTIVE,
            "deadline": days(35),
            "priority_level": Opportunity.PriorityLevel.LOW,
            "lifecycle_status": Opportunity.LifecycleStatus.DISCOVERED,
            "notes": "Quick-win accessible grant if EGI incorporates any arts expression elements.",
        },
    ]
    for d in opps_data:
        Opportunity.objects.create(**d, project=project, last_reviewed_at=now())
        print(f"  Opportunity: {d['name']}")

    # ── 7. Funding Partner Organizations ──────────────────────────────────
    print("Seeding funding partner organizations…")
    funding_partners = [
        {
            "name": "Girls Inc. National",
            "partner_type": FundingPartnerOrg.PartnerType.NONPROFIT,
            "geography": ["National"],
            "focus_areas": ["girls empowerment", "programming", "research"],
            "beneficiaries": ["girls ages 9-18", "young women"],
            "collaboration_opportunities": [
                "Curriculum sharing",
                "National funder introductions",
                "Affiliate recognition",
                "Advocacy and policy influence",
            ],
            "website": "https://www.girlsinc.org",
            "notes": "Strategic national partner. EGI's model closely mirrors Girls Inc. affiliate approach.",
            "intelligence_status": FundingPartnerOrg.IntelligenceStatus.ACTIVE,
        },
        {
            "name": "Orange County Public Schools",
            "partner_type": FundingPartnerOrg.PartnerType.SCHOOL_DISTRICT,
            "geography": ["Orange County", "Orlando"],
            "focus_areas": ["education", "youth development", "after-school"],
            "beneficiaries": ["K-12 students", "girls"],
            "collaboration_opportunities": [
                "School-based program delivery",
                "Enrollment pipeline via teacher referrals",
                "Access to school facilities",
                "Co-programming with counselors",
            ],
            "website": "https://www.ocps.net",
            "notes": "Critical access partner. MOU could significantly expand EGI's reach to girls in schools.",
            "intelligence_status": FundingPartnerOrg.IntelligenceStatus.ACTIVE,
        },
        {
            "name": "University of Central Florida",
            "partner_type": FundingPartnerOrg.PartnerType.UNIVERSITY_COLLEGE,
            "geography": ["Orlando", "Central Florida"],
            "focus_areas": ["mentorship", "career exploration", "research", "volunteers"],
            "beneficiaries": ["youth", "girls", "aspiring college students"],
            "collaboration_opportunities": [
                "College student mentor pipeline",
                "Campus visits for EGI participants",
                "Career exploration programming",
                "Research partnership and grant co-applicant",
            ],
            "website": "https://www.ucf.edu",
            "notes": "UCF students are a potential mentor pipeline. Partnership strengthens career readiness.",
            "intelligence_status": FundingPartnerOrg.IntelligenceStatus.MONITORING,
        },
        {
            "name": "AdventHealth Community Health Programs",
            "partner_type": FundingPartnerOrg.PartnerType.HEALTHCARE_ORGANIZATION,
            "geography": ["Orlando", "Central Florida"],
            "focus_areas": ["health and wellness", "youth health", "community programs"],
            "beneficiaries": ["youth", "girls", "families"],
            "collaboration_opportunities": [
                "Health & wellness curriculum support",
                "Health screenings and education events",
                "Co-programming on mental wellness",
                "Community benefit sponsorship",
            ],
            "website": "https://www.adventhealth.com",
            "notes": "EGI's health & wellness program creates natural alignment. AdventHealth has a community benefit program.",
            "intelligence_status": FundingPartnerOrg.IntelligenceStatus.PROSPECT,
        },
        {
            "name": "Heart of Florida United Way",
            "partner_type": FundingPartnerOrg.PartnerType.OTHER,
            "geography": ["Orlando", "Orange County", "Osceola", "Seminole"],
            "focus_areas": ["youth success", "education", "financial stability", "health"],
            "beneficiaries": ["youth", "families", "low-income residents"],
            "collaboration_opportunities": [
                "United Way funded partner designation",
                "Workplace giving campaign access",
                "Coalition membership",
                "Capacity resources and peer learning",
            ],
            "website": "https://www.hfuw.org",
            "notes": "United Way designation can unlock corporate giving campaigns. Youth Success focus aligns directly with EGI.",
            "intelligence_status": FundingPartnerOrg.IntelligenceStatus.PROSPECT,
        },
    ]
    for d in funding_partners:
        FundingPartnerOrg.objects.create(**d, active=True, last_reviewed_at=now())
        print(f"  Funding Partner: {d['name']}")

    # ── 8. Resource Providers ─────────────────────────────────────────────
    print("Seeding resource providers…")
    resources = [
        {
            "name": "Florida Nonprofit Alliance",
            "resource_type": ResourceProvider.ResourceType.NONPROFIT_SUPPORT_CENTER,
            "geography": ["Florida"],
            "focus_areas": ["nonprofit management", "capacity building", "training", "advocacy"],
            "resource_categories": ["training", "consulting", "advocacy", "peer network"],
            "eligibility_notes": "Florida nonprofits. Membership-based with training, webinars, and technical assistance.",
            "website": "https://www.floridanonprofits.org",
            "notes": "State association for Florida nonprofits. Low-cost training, grant writing support, HR resources.",
            "active": True,
        },
        {
            "name": "TechSoup — Nonprofit Software Donations",
            "resource_type": ResourceProvider.ResourceType.SOFTWARE_DONATION_PROGRAM,
            "geography": ["National"],
            "focus_areas": ["technology", "software", "nonprofit capacity"],
            "resource_categories": ["software", "cloud services", "cybersecurity", "hardware"],
            "eligibility_notes": "501(c)(3) nonprofits. Deeply discounted or donated software (Microsoft, Adobe, Salesforce, etc.).",
            "website": "https://www.techsoup.org",
            "notes": "EGI can access Microsoft 365, Adobe Creative Cloud, and Salesforce Nonprofit at deep discount.",
            "active": True,
        },
        {
            "name": "Points of Light — HandsOn Network",
            "resource_type": ResourceProvider.ResourceType.VOLUNTEER_NETWORK,
            "geography": ["National", "Orlando"],
            "focus_areas": ["volunteer recruitment", "community service", "corporate volunteers"],
            "resource_categories": ["volunteers", "corporate partnerships", "service events"],
            "eligibility_notes": "Nonprofits that engage volunteers. Free registration for posting volunteer opportunities.",
            "website": "https://www.pointsoflight.org",
            "notes": "Volunteer pipeline for EGI's mentorship and community service programs.",
            "active": True,
        },
        {
            "name": "AmeriCorps VISTA Program",
            "resource_type": ResourceProvider.ResourceType.AMERICORPS_NATIONAL_SERVICE,
            "geography": ["National", "Florida"],
            "focus_areas": ["capacity building", "poverty reduction", "nonprofit staffing"],
            "resource_categories": ["national service members", "capacity support", "community outreach"],
            "eligibility_notes": "Nonprofits with anti-poverty mission. VISTA members serve 1 year building capacity.",
            "website": "https://www.americorps.gov/serve/fit-finder/americorps-vista",
            "notes": "A VISTA member could help EGI build grant infrastructure, volunteer systems, or expand enrollment.",
            "active": True,
        },
        {
            "name": "Nonprofit Center of Central Florida",
            "resource_type": ResourceProvider.ResourceType.CAPACITY_BUILDING_ORGANIZATION,
            "geography": ["Orlando", "Central Florida"],
            "focus_areas": ["board development", "strategic planning", "grant writing", "financial management"],
            "resource_categories": ["consulting", "training", "board matching", "grant writing workshops"],
            "eligibility_notes": "Central Florida nonprofits. Offers subsidized consulting and training for small organizations.",
            "website": "https://www.nonprofitcenterfl.org",
            "notes": "Local capacity org. Grant writing workshops and board consulting directly useful to EGI's growth stage.",
            "active": True,
        },
    ]
    for d in resources:
        ResourceProvider.objects.create(**d)
        print(f"  Resource: {d['name']}")

    # ── 9. Government Entities ────────────────────────────────────────────
    print("Seeding government entities…")
    gov_entities = [
        {
            "name": "City of Orlando — Families, Parks & Recreation",
            "entity_type": GovernmentEntity.EntityType.CITY_GOVERNMENT,
            "geography": ["Orlando"],
            "focus_areas": ["youth programs", "community services", "parks", "girls programming"],
            "department_or_office": "Families, Parks & Recreation Department",
            "opportunity_lanes": [
                "Youth Program Grants",
                "Community Event Partnerships",
                "City RFPs for youth services",
            ],
            "website": "https://www.orlando.gov/Parks-the-Environment",
            "notes": "City department that funds and partners with youth-serving nonprofits in Orlando.",
            "active": True,
        },
        {
            "name": "Orange County Community & Family Services",
            "entity_type": GovernmentEntity.EntityType.COUNTY_GOVERNMENT,
            "geography": ["Orange County", "Orlando"],
            "focus_areas": ["youth services", "girls programs", "community development", "prevention"],
            "department_or_office": "Community & Family Services Division",
            "opportunity_lanes": [
                "Youth Initiative Contracts",
                "Prevention Programs",
                "Community Development Block Grant (CDBG)",
            ],
            "website": "https://www.ocfl.net/commfam",
            "notes": "County-level funder and service partner. CDBG funds relevant if EGI serves low-income neighborhoods.",
            "active": True,
        },
        {
            "name": "Florida Dept. of Children & Families — Region 7",
            "entity_type": GovernmentEntity.EntityType.OTHER,
            "geography": ["Central Florida", "Florida"],
            "focus_areas": ["child welfare", "prevention", "at-risk youth", "family services"],
            "department_or_office": "Region 7 (Central Florida)",
            "opportunity_lanes": [
                "Prevention Programs",
                "Youth Mentoring Contracts",
                "Community-Based Care partnerships",
            ],
            "website": "https://www.myflfamilies.com",
            "notes": "State agency for child and family services. Contracts for prevention and mentoring for at-risk girls.",
            "active": True,
        },
    ]
    for d in gov_entities:
        GovernmentEntity.objects.create(**d)
        print(f"  Gov Entity: {d['name']}")

    # ── 10. Relationship Partners (signals app) ───────────────────────────
    print("Seeding relationship partners…")
    rel_partners = [
        ("Girls Inc. National", RelPartnerOrg.PartnerType.FUNDING_PARTNER, RelPartnerOrg.RelationshipStrength.DEVELOPING),
        ("Heart of Florida United Way", RelPartnerOrg.PartnerType.FUNDING_PARTNER, RelPartnerOrg.RelationshipStrength.UNKNOWN),
        ("Orange County Public Schools", RelPartnerOrg.PartnerType.COMMUNITY_PARTNER, RelPartnerOrg.RelationshipStrength.DEVELOPING),
        ("University of Central Florida", RelPartnerOrg.PartnerType.ACADEMIC_PARTNER, RelPartnerOrg.RelationshipStrength.UNKNOWN),
        ("Florida Nonprofit Alliance", RelPartnerOrg.PartnerType.SERVICE_PARTNER, RelPartnerOrg.RelationshipStrength.ESTABLISHED),
    ]
    for name, ptype, strength in rel_partners:
        RelPartnerOrg.objects.create(
            project=project,
            organization_name=name,
            partner_type=ptype,
            relationship_strength=strength,
            status=RelPartnerOrg.Status.ACTIVE,
        )

    # ── 11. Organization Contacts ─────────────────────────────────────────
    print("Seeding organization contacts…")
    contacts = [
        ("Program Officer", "Community Foundation of Central Florida", "program_officer"),
        ("Community Relations Manager", "Walt Disney World Community Fund", "corporate_contact"),
        ("Grant Manager", "Dr. Phillips Charities", "funder"),
        ("Development Officer", "Heart of Florida United Way", "partner"),
        ("Community Schools Coordinator", "Orange County Public Schools", "partner"),
        ("UCF Volunteer Coordinator", "University of Central Florida", "partner"),
    ]
    for name, org_name, ctype in contacts:
        OrganizationContact.objects.create(
            project=project,
            name=name,
            organization=org_name,
            contact_type=ctype,
            notes=f"Key contact at {org_name} for partnership and funding conversations.",
        )

    # ── 12. Celebrations ──────────────────────────────────────────────────
    print("Seeding celebrations…")
    celebrations = [
        ("43+ Girls Impacted in 2025", Celebration.CelebrationType.IMPACT_MILESTONE,
         "EGI reached and directly served 43+ girls through programming in 2025."),
        ("$11,000+ Awarded to Participants", Celebration.CelebrationType.FUNDING_SECURED,
         "Over $11,000 in scholarships and awards distributed to EGI program participants."),
        ("5,000 Families Reached Through Service", Celebration.CelebrationType.COMMUNITY_ACHIEVEMENT,
         "EGI's community service programs reached 5,000 families in Central Florida."),
        ("2025 EGI Award Gala", Celebration.CelebrationType.ORGANIZATION_MILESTONE,
         "Annual gala celebrating participant achievements and program milestones."),
        ("Active 501(c)(3) Status", Celebration.CelebrationType.ORGANIZATION_MILESTONE,
         "EGI maintains active 501(c)(3) status — key eligibility credential for grant applications."),
        ("Multi-Platform Social Media Presence", Celebration.CelebrationType.ORGANIZATION_MILESTONE,
         "Active Instagram, Facebook, LinkedIn, and YouTube — key for funder visibility."),
        ("Network for Good Online Giving Infrastructure", Celebration.CelebrationType.ORGANIZATION_MILESTONE,
         "Online donation infrastructure active through Network for Good — enabling year-round giving."),
    ]
    for title, ctype, desc in celebrations:
        Celebration.objects.create(
            project=project,
            title=title,
            celebration_type=ctype,
            description=desc,
        )

    # ── 13. Evidence Library ──────────────────────────────────────────────
    print("Seeding evidence library…")
    evidence = [
        ("43 Girls Directly Served (2025)", EvidenceLibraryItem.EvidenceType.OUTCOME_METRIC,
         "43 girls directly served; age range 9-18; life skills, career, health & wellness, education, community service."),
        ("$11,000+ Participant Awards (2025)", EvidenceLibraryItem.EvidenceType.OUTCOME_METRIC,
         "$11,000+ awarded to participants in 2025; demonstrates direct financial benefit to program participants."),
        ("5,000 Families Reached Through Service", EvidenceLibraryItem.EvidenceType.PROGRAM_RESULT,
         "5,000 families reached through EGI-organized community service initiatives in 2025."),
        ("IRS 501(c)(3) Determination Letter", EvidenceLibraryItem.EvidenceType.OTHER,
         "IRS 501(c)(3) determination letter confirming tax-exempt charitable status."),
        ("Social Media Presence & Engagement", EvidenceLibraryItem.EvidenceType.MEDIA_MENTION,
         "Active Instagram, Facebook, LinkedIn, YouTube with documented follower base and engagement."),
        ("2025 Award Gala Documentation", EvidenceLibraryItem.EvidenceType.IMPACT_STORY,
         "Photos, attendance records, and recognition documentation from 2025 EGI Award Gala."),
        ("POWER Framework Curriculum", EvidenceLibraryItem.EvidenceType.PROGRAM_RESULT,
         "Documented POWER curriculum: Persevere, Overcome, Win, Excel, Reform — life skills and empowerment framework."),
        ("Participant & Family Testimonials", EvidenceLibraryItem.EvidenceType.TESTIMONIAL,
         "Testimonials from EGI program participants and families about program impact."),
    ]
    for title, etype, notes in evidence:
        EvidenceLibraryItem.objects.create(
            project=project,
            title=title,
            evidence_type=etype,
            notes=notes,
            status=EvidenceLibraryItem.Status.AVAILABLE,
        )

    # ── 14. Document Vault ────────────────────────────────────────────────
    print("Seeding document vault…")
    docs = [
        ("IRS Determination Letter", DocumentVaultItem.DocumentType.IRS_DETERMINATION_LETTER, "available"),
        ("W-9 Form", DocumentVaultItem.DocumentType.W9, "needs_update"),
        ("Annual Budget (Current Year)", DocumentVaultItem.DocumentType.ANNUAL_BUDGET, "missing"),
        ("Board of Directors List", DocumentVaultItem.DocumentType.BOARD_LIST, "missing"),
        ("2025 Annual / Impact Report", DocumentVaultItem.DocumentType.ANNUAL_REPORT, "available"),
        ("Program Budget — Life Skills", DocumentVaultItem.DocumentType.PROGRAM_BUDGET, "missing"),
        ("Financial Audit / Statement", DocumentVaultItem.DocumentType.AUDIT_FINANCIAL_STATEMENT, "missing"),
        ("Strategic Plan", DocumentVaultItem.DocumentType.STRATEGIC_PLAN, "missing"),
        ("Program / Curriculum Overview", DocumentVaultItem.DocumentType.OTHER, "available"),
    ]
    for title, dtype, status in docs:
        DocumentVaultItem.objects.create(
            project=project,
            title=title,
            document_type=dtype,
            status=status,
        )

    # ── 15. Pilot Profile ─────────────────────────────────────────────────
    print("Seeding pilot profile…")
    PilotProfile.objects.create(
        project=project,
        organization_name="Empowered Girls Inc.",
        contact_name="Empowered Girls Inc. Team",
        email="info@empoweredgirlsinc.org",
        website="https://www.empoweredgirlsinc.org",
        lifecycle_status=PilotProfile.LifecycleStatus.SNAPSHOT_IN_PROGRESS,
        mission=(
            "Developing young girls into strong, empowered women who can overcome barriers "
            "and lead successful, productive lives. POWER: Persevere, Overcome, Win, Excel, Reform."
        ),
        location="Orlando, Florida (P.O. Box 681102, Orlando, FL 32868)",
        annual_budget_range="Under $250,000",
        primary_programs=(
            "Life Skills (POWER framework), Career Development & Exploration, "
            "Health & Wellness, Education Support & Scholarships, Community Service"
        ),
        communities_served=(
            "Girls ages 9-18 in Orlando and Central Florida, with focus on underserved "
            "communities. Families reached through community service programming."
        ),
        geographic_reach="Orlando, Orange County, Central Florida",
        current_revenue_sources=(
            "Individual donations (Network for Good), event revenue (Award Gala), "
            "corporate sponsorships, in-kind contributions. No major grant funding yet identified."
        ),
        funding_challenges=(
            "Small budget, limited grant history, no dedicated development staff. "
            "Need to build funder relationships and grant-ready documentation."
        ),
        top_goals=(
            "1. Secure first major foundation grant in 2025-2026. "
            "2. Formalize school partnership with Orange County Public Schools. "
            "3. Expand to serve 100+ girls annually. "
            "4. Build fundraising capacity and operations infrastructure."
        ),
        biggest_challenges=(
            "Capacity constraints (staff time for grant writing), documentation gaps "
            "(no formal strategic plan, limited outcome tracking), "
            "limited brand visibility outside Orlando community."
        ),
        snapshot_status=PilotProfile.SnapshotStatus.BUILDING_OPPORTUNITY_WEB,
        assigned_reviewer="Marcus Scott",
        snapshot_notes=(
            "Live test org for Anansi Atlas platform demo. "
            "Real organization with verified 501(c)(3) status. "
            "2025 impact data: 43+ girls, $11K+ in awards, 5,000 families."
        ),
    )

    # ── Summary ───────────────────────────────────────────────────────────
    print()
    print("=" * 55)
    print("  Empowered Girls Inc. is now the active organization")
    print("=" * 55)
    print(f"  Opportunities:    {Opportunity.objects.count()}")
    print(f"  Funders:          {Funder.objects.count()}")
    print(f"  Funding Partners: {FundingPartnerOrg.objects.count()}")
    print(f"  Resources:        {ResourceProvider.objects.count()}")
    print(f"  Gov Entities:     {GovernmentEntity.objects.count()}")
    print(f"  Rel Partners:     {RelPartnerOrg.objects.count()}")
    print(f"  Contacts:         {OrganizationContact.objects.count()}")
    print(f"  Celebrations:     {Celebration.objects.count()}")
    print(f"  Evidence:         {EvidenceLibraryItem.objects.count()}")
    print(f"  Documents:        {DocumentVaultItem.objects.count()}")
    print(f"  Pilot Profiles:   {PilotProfile.objects.count()}")
    print()
    print("Next: make run  →  http://127.0.0.1:8000/admin/")
