"""
Seed script: diverse funder/partner/opportunity data for Anansi Atlas.

Covers 6 common nonprofit archetypes beyond workforce development:
  - Youth Arts & Culture
  - Housing & Homelessness
  - Food Security & Hunger
  - Mental Health & Wellness
  - Immigration & Refugee Services
  - Early Childhood & Family Support

Run from the project root:
  python seeds/seed_diverse_funders.py

Or from Render shell:
  python seeds/seed_diverse_funders.py
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "openoutreach.settings")
django.setup()

from openoutreach.signals.research import import_research_data

# ── Universal: National funders active across all sectors ─────────────────────

UNIVERSAL_FUNDERS = [
    {
        "name": "Robert Wood Johnson Foundation",
        "funder_type": "family_foundation",
        "geography": ["National"],
        "focus_areas": ["Health", "Health Equity", "Social Determinants of Health", "Mental Health"],
        "beneficiaries": ["Low-income individuals", "Communities of color", "Children", "Families"],
        "eligibility_notes": "501(c)(3) required. Priorities: health equity, social determinants. Accepts LOIs.",
        "website": "https://www.rwjf.org",
        "notes": "One of the largest health-focused foundations in the US. Also funds food security, housing, and community health.",
        "source_urls": ["https://www.rwjf.org/en/grants.html"],
        "source_references": [],
        "source_notes": "RWJF grants page",
        "verification_status": "unverified",
    },
    {
        "name": "W.K. Kellogg Foundation",
        "funder_type": "family_foundation",
        "geography": ["National", "Michigan", "Mississippi", "New Mexico", "New Orleans"],
        "focus_areas": ["Early Childhood", "Education", "Health", "Food Systems", "Racial Equity"],
        "beneficiaries": ["Children", "Families", "Communities of color", "Low-income individuals"],
        "eligibility_notes": "Invitations only for national grants. Community grants open in priority geographies.",
        "website": "https://www.wkkf.org",
        "notes": "Strong focus on thriving children, working families, and equitable communities.",
        "source_urls": ["https://www.wkkf.org/grants"],
        "source_references": [],
        "source_notes": "WKKF grants page",
        "verification_status": "unverified",
    },
    {
        "name": "Ford Foundation",
        "funder_type": "family_foundation",
        "geography": ["National", "International"],
        "focus_areas": ["Racial Justice", "Economic Justice", "Gender Justice", "LGBTQ+ Rights", "Immigration"],
        "beneficiaries": ["Communities of color", "Immigrants", "LGBTQ+ individuals", "Low-income individuals"],
        "eligibility_notes": "Invitation-based for most programs. Build Field program for advocacy/movement orgs.",
        "website": "https://www.fordfoundation.org",
        "notes": "Focus on reducing inequality and supporting social justice movements.",
        "source_urls": ["https://www.fordfoundation.org/work/our-grants/"],
        "source_references": [],
        "source_notes": "Ford Foundation grants",
        "verification_status": "unverified",
    },
    {
        "name": "Annie E. Casey Foundation",
        "funder_type": "family_foundation",
        "geography": ["National"],
        "focus_areas": ["Child Welfare", "Youth Development", "Family Economic Security", "Community Change"],
        "beneficiaries": ["Children", "Youth", "Families", "Communities of color"],
        "eligibility_notes": "Primarily invitation-based. KIDS COUNT network grants open. LOIs accepted.",
        "website": "https://www.aecf.org",
        "notes": "Leading funder for vulnerable children and families. KIDS COUNT data network.",
        "source_urls": ["https://www.aecf.org/work/grants"],
        "source_references": [],
        "source_notes": "AECF grants",
        "verification_status": "unverified",
    },
    {
        "name": "JPMorgan Chase Foundation",
        "funder_type": "corporate_foundation",
        "geography": ["National", "New York", "Chicago", "Los Angeles", "Detroit", "Miami"],
        "focus_areas": ["Workforce Development", "Small Business", "Financial Health", "Community Development", "Housing"],
        "beneficiaries": ["Low-income individuals", "Communities of color", "Small business owners"],
        "eligibility_notes": "501(c)(3) required. Apply via PowerPhilanthropy or direct solicitation. Focus cities get priority.",
        "website": "https://www.jpmorganchase.com/impact/philanthropy",
        "notes": "Major corporate funder. AdvancingCities and PRO Neighborhoods programs for community development.",
        "source_urls": ["https://www.jpmorganchase.com/impact/philanthropy/grant-guidelines"],
        "source_references": [],
        "source_notes": "Chase philanthropy guidelines",
        "verification_status": "unverified",
    },
    {
        "name": "Bank of America Charitable Foundation",
        "funder_type": "corporate_foundation",
        "geography": ["National"],
        "focus_areas": ["Economic Mobility", "Housing", "Workforce Development", "Health", "Hunger"],
        "beneficiaries": ["Low-income individuals", "Communities of color", "Families"],
        "eligibility_notes": "501(c)(3) required. Apply via online portal. Economic mobility priority.",
        "website": "https://about.bankofamerica.com/en/making-an-impact/charitable-foundation-funding",
        "notes": "National Neighborhood Excellence Initiative. Strong affordable housing focus.",
        "source_urls": ["https://about.bankofamerica.com/en/making-an-impact/charitable-foundation-funding"],
        "source_references": [],
        "source_notes": "BofA charitable foundation",
        "verification_status": "unverified",
    },
    {
        "name": "Walmart Foundation",
        "funder_type": "corporate_foundation",
        "geography": ["National"],
        "focus_areas": ["Hunger Relief", "Workforce Development", "Sustainability", "Disaster Relief"],
        "beneficiaries": ["Low-income individuals", "Families", "Workers"],
        "eligibility_notes": "Must be 501(c)(3). Apply via online portal. Hunger and workforce priorities.",
        "website": "https://walmart.org",
        "notes": "Hunger: $250M+ committed. Opportunity: $100M for workforce training aligned to retail/supply chain.",
        "source_urls": ["https://walmart.org/how-we-give/walmart-foundation"],
        "source_references": [],
        "source_notes": "Walmart Foundation website",
        "verification_status": "unverified",
    },
    {
        "name": "Community Development Block Grant (CDBG)",
        "funder_type": "federal_government",
        "geography": ["National"],
        "focus_areas": ["Housing", "Community Development", "Economic Development", "Social Services"],
        "beneficiaries": ["Low-income individuals", "Communities of color"],
        "eligibility_notes": "Administered by local governments (city/county). Apply to your local CDBG office, not HUD directly.",
        "website": "https://www.hud.gov/program_offices/comm_planning/cdbg",
        "notes": "Flexible federal funding distributed to localities. Contact your city/county planning department.",
        "source_urls": ["https://www.hud.gov/program_offices/comm_planning/cdbg"],
        "source_references": [],
        "source_notes": "HUD CDBG program page",
        "verification_status": "unverified",
    },
]

# ── Youth Arts & Culture ──────────────────────────────────────────────────────

YOUTH_ARTS_FUNDERS = [
    {
        "name": "National Endowment for the Arts",
        "funder_type": "federal_government",
        "geography": ["National"],
        "focus_areas": ["Arts & Culture", "Youth Development", "Arts Education", "Community Arts"],
        "beneficiaries": ["Youth", "Communities of color", "Underserved communities"],
        "eligibility_notes": "501(c)(3) required. Grants for Art Works: $10K–100K. Deadline varies by cycle. SAM.gov registration required.",
        "website": "https://www.arts.gov",
        "notes": "Primary federal arts funder. Direct grants and state arts agency pass-throughs.",
        "source_urls": ["https://www.arts.gov/grants"],
        "source_references": [],
        "source_notes": "NEA grants page",
        "verification_status": "unverified",
    },
    {
        "name": "Doris Duke Charitable Foundation",
        "funder_type": "family_foundation",
        "geography": ["National"],
        "focus_areas": ["Arts", "Jazz", "Theatre", "Dance", "Environment", "Child Abuse Prevention"],
        "beneficiaries": ["Artists", "Youth", "Performing arts organizations"],
        "eligibility_notes": "Invitation-based primarily. Arts program focuses on contemporary performing arts.",
        "website": "https://www.ddcf.org",
        "notes": "Strong performing arts focus. Theatre, jazz, and dance organizations.",
        "source_urls": ["https://www.ddcf.org/grants/"],
        "source_references": [],
        "source_notes": "DDCF grants",
        "verification_status": "unverified",
    },
    {
        "name": "Surdna Foundation",
        "funder_type": "family_foundation",
        "geography": ["National"],
        "focus_areas": ["Arts", "Youth Development", "Community Development", "Sustainable Environments"],
        "beneficiaries": ["Youth", "Communities of color", "Low-income communities"],
        "eligibility_notes": "Invitation-based. Arts and youth programs in urban areas.",
        "website": "https://surdna.org",
        "notes": "Thriving Cultures program: arts and culture for community wellbeing.",
        "source_urls": ["https://surdna.org/grants/"],
        "source_references": [],
        "source_notes": "Surdna Foundation grants",
        "verification_status": "unverified",
    },
    {
        "name": "Mellon Foundation",
        "funder_type": "family_foundation",
        "geography": ["National"],
        "focus_areas": ["Arts & Culture", "Higher Education", "Public Knowledge", "Humanities"],
        "beneficiaries": ["Artists", "Students", "Communities of color"],
        "eligibility_notes": "Invitation-based for arts. Arts and Culture program: museums, performing arts, cultural heritage.",
        "website": "https://www.mellon.org",
        "notes": "Largest arts and humanities funder in the US. Cultural equity focus.",
        "source_urls": ["https://www.mellon.org/grants"],
        "source_references": [],
        "source_notes": "Mellon Foundation grants",
        "verification_status": "unverified",
    },
]

YOUTH_ARTS_OPPORTUNITIES = [
    {
        "name": "NEA Grants for Art Works",
        "opportunity_type": "grant",
        "source_type": "government",
        "source_name": "National Endowment for the Arts",
        "geography": ["National"],
        "focus_areas": ["Arts & Culture", "Youth Development", "Arts Education"],
        "beneficiaries": ["Youth", "Underserved communities"],
        "eligibility_notes": "501(c)(3) or government entity. Minimum $10K match required. SAM.gov registration.",
        "funding_amount": 50000,
        "deadline": None,
        "priority_level": "high",
        "status": "active",
        "notes": "Core NEA grant program. Awards $10K–$100K for arts projects with broad public benefit.",
        "source_urls": ["https://www.arts.gov/grants/grants-for-arts-projects"],
        "source_references": [],
        "source_notes": "NEA website",
        "verification_status": "unverified",
    },
    {
        "name": "State Arts Agency General Operating Support",
        "opportunity_type": "grant",
        "source_type": "government",
        "source_name": "State Arts Agency (NEA pass-through)",
        "geography": ["State"],
        "focus_areas": ["Arts & Culture", "Arts Education"],
        "beneficiaries": ["General public", "Youth"],
        "eligibility_notes": "Must be state-based 501(c)(3). Contact your state arts agency for deadlines and amounts.",
        "funding_amount": 25000,
        "deadline": None,
        "priority_level": "high",
        "status": "active",
        "notes": "Every state has an arts agency distributing NEA pass-through funds. Often easier to win than direct NEA.",
        "source_urls": ["https://nasaa-arts.org/nasaa_research/state-arts-agency-profiles/"],
        "source_references": [],
        "source_notes": "NASAA state arts agency directory",
        "verification_status": "unverified",
    },
]

# ── Housing & Homelessness ────────────────────────────────────────────────────

HOUSING_FUNDERS = [
    {
        "name": "Enterprise Community Partners",
        "funder_type": "other",
        "geography": ["National"],
        "focus_areas": ["Affordable Housing", "Community Development", "Economic Mobility"],
        "beneficiaries": ["Low-income individuals", "Families", "Homeless individuals"],
        "eligibility_notes": "501(c)(3) or CDFI. Grant programs vary by region and initiative. Apply online.",
        "website": "https://www.enterprisecommunity.org",
        "notes": "Leading affordable housing nonprofit and funder. Enterprise Rose Architectural Fellowship for design innovation.",
        "source_urls": ["https://www.enterprisecommunity.org/financing-and-development/grants"],
        "source_references": [],
        "source_notes": "Enterprise grants page",
        "verification_status": "unverified",
    },
    {
        "name": "NeighborWorks America",
        "funder_type": "other",
        "geography": ["National"],
        "focus_areas": ["Affordable Housing", "Homeownership", "Community Development", "Financial Counseling"],
        "beneficiaries": ["Low-income individuals", "Families", "First-time homebuyers"],
        "eligibility_notes": "Must be a NeighborWorks network organization. Network membership required.",
        "website": "https://www.neighborworks.org",
        "notes": "Congressional charter. $250M+ annually to network organizations for housing and community development.",
        "source_urls": ["https://www.neighborworks.org/funding"],
        "source_references": [],
        "source_notes": "NeighborWorks funding page",
        "verification_status": "unverified",
    },
    {
        "name": "HUD Continuum of Care (CoC) Program",
        "funder_type": "federal_government",
        "geography": ["National"],
        "focus_areas": ["Homelessness", "Transitional Housing", "Permanent Supportive Housing"],
        "beneficiaries": ["Homeless individuals", "Families experiencing homelessness", "Veterans"],
        "eligibility_notes": "Must apply through local CoC lead agency. Not a direct federal application. Contact your local CoC.",
        "website": "https://www.hudexchange.info/programs/coc/",
        "notes": "Primary federal homeless services funding stream. Competitive renewal + new project grants.",
        "source_urls": ["https://www.hudexchange.info/programs/coc/coc-program-competition/"],
        "source_references": [],
        "source_notes": "HUD CoC program page",
        "verification_status": "unverified",
    },
    {
        "name": "Home Depot Foundation",
        "funder_type": "corporate_foundation",
        "geography": ["National"],
        "focus_areas": ["Affordable Housing", "Veteran Housing", "Disaster Relief", "Community Development"],
        "beneficiaries": ["Veterans", "Low-income individuals", "Disaster survivors"],
        "eligibility_notes": "501(c)(3) required. Veteran housing is the top priority. Apply online.",
        "website": "https://homedepotfoundation.org",
        "notes": "Veteran housing and home repair a priority. $500M+ committed to veteran home improvement.",
        "source_urls": ["https://homedepotfoundation.org/grant-resources/"],
        "source_references": [],
        "source_notes": "Home Depot Foundation grants",
        "verification_status": "unverified",
    },
]

HOUSING_OPPORTUNITIES = [
    {
        "name": "HUD CoC New Project Application",
        "opportunity_type": "grant",
        "source_type": "government",
        "source_name": "HUD / Local CoC Lead Agency",
        "geography": ["Local"],
        "focus_areas": ["Homelessness", "Permanent Supportive Housing"],
        "beneficiaries": ["Homeless individuals", "Families experiencing homelessness"],
        "eligibility_notes": "Must work through local CoC lead. Contact your city/county CoC coordinator.",
        "funding_amount": 200000,
        "deadline": None,
        "priority_level": "high",
        "status": "active",
        "notes": "Annual competition. New projects for rapid rehousing, transitional housing, or permanent supportive housing.",
        "source_urls": ["https://www.hudexchange.info/programs/coc/"],
        "source_references": [],
        "source_notes": "HUD CoC program",
        "verification_status": "unverified",
    },
]

# ── Food Security & Hunger ────────────────────────────────────────────────────

FOOD_SECURITY_FUNDERS = [
    {
        "name": "Feeding America",
        "funder_type": "other",
        "geography": ["National"],
        "focus_areas": ["Food Security", "Hunger Relief", "Food Rescue"],
        "beneficiaries": ["Food-insecure individuals", "Families", "Children", "Seniors"],
        "eligibility_notes": "Must be a Feeding America network food bank. Network membership required.",
        "website": "https://www.feedingamerica.org",
        "notes": "Largest hunger-relief organization in the US. Network food banks + disaster response.",
        "source_urls": ["https://www.feedingamerica.org/our-work/partner-with-us"],
        "source_references": [],
        "source_notes": "Feeding America partner page",
        "verification_status": "unverified",
    },
    {
        "name": "USDA Community Food Projects Competitive Grant Program",
        "funder_type": "federal_government",
        "geography": ["National"],
        "focus_areas": ["Food Security", "Community Food Systems", "Urban Agriculture", "Food Access"],
        "beneficiaries": ["Low-income communities", "Food-insecure individuals"],
        "eligibility_notes": "501(c)(3) or tribal organization. 1:1 match required. Competitive. $35K–400K.",
        "website": "https://www.nifa.usda.gov/grants/programs/community-food-projects-competitive-grant-program",
        "notes": "USDA/NIFA program. Community food projects that help food insecure communities become self-sufficient.",
        "source_urls": ["https://www.nifa.usda.gov/grants/programs/community-food-projects-competitive-grant-program"],
        "source_references": [],
        "source_notes": "USDA NIFA grants",
        "verification_status": "unverified",
    },
    {
        "name": "Share Our Strength / No Kid Hungry",
        "funder_type": "other",
        "geography": ["National"],
        "focus_areas": ["Child Hunger", "Food Security", "School Breakfast", "Summer Meals"],
        "beneficiaries": ["Children", "Students", "Families"],
        "eligibility_notes": "501(c)(3) required. Focus on school meals and summer hunger programs.",
        "website": "https://www.nokidhungry.org",
        "notes": "No Kid Hungry campaign grants for school breakfast expansion and summer meal programs.",
        "source_urls": ["https://www.nokidhungry.org/what-we-do/grants"],
        "source_references": [],
        "source_notes": "No Kid Hungry grants page",
        "verification_status": "unverified",
    },
    {
        "name": "Publix Super Markets Charities",
        "funder_type": "corporate_foundation",
        "geography": ["Southeast US", "Florida", "Georgia", "Alabama", "South Carolina", "Tennessee", "North Carolina", "Virginia"],
        "focus_areas": ["Hunger Relief", "Early Literacy", "Youth Development"],
        "beneficiaries": ["Food-insecure individuals", "Children", "Families"],
        "eligibility_notes": "501(c)(3) in Publix operating states. Apply online through their grants portal.",
        "website": "https://www.publix.com/pub/about/charity",
        "notes": "Southeast-focused. Hunger is top priority. $30M+ annually.",
        "source_urls": ["https://www.publix.com/pub/about/charity/grant-requests.html"],
        "source_references": [],
        "source_notes": "Publix charities",
        "verification_status": "unverified",
    },
]

FOOD_SECURITY_OPPORTUNITIES = [
    {
        "name": "USDA Community Food Projects Grant",
        "opportunity_type": "grant",
        "source_type": "government",
        "source_name": "USDA NIFA",
        "geography": ["National"],
        "focus_areas": ["Food Security", "Community Food Systems"],
        "beneficiaries": ["Low-income communities"],
        "eligibility_notes": "501(c)(3) required. 1:1 match. Up to $400K.",
        "funding_amount": 400000,
        "deadline": None,
        "priority_level": "high",
        "status": "active",
        "notes": "Annual competitive grant for community food projects.",
        "source_urls": ["https://www.nifa.usda.gov/grants/programs/community-food-projects-competitive-grant-program"],
        "source_references": [],
        "source_notes": "USDA NIFA",
        "verification_status": "unverified",
    },
]

# ── Mental Health & Wellness ──────────────────────────────────────────────────

MENTAL_HEALTH_FUNDERS = [
    {
        "name": "SAMHSA Grants",
        "funder_type": "federal_government",
        "geography": ["National"],
        "focus_areas": ["Mental Health", "Substance Use Disorder", "Crisis Services", "Prevention"],
        "beneficiaries": ["Adults with mental illness", "Youth", "Veterans", "Underserved communities"],
        "eligibility_notes": "501(c)(3) or government entity. Grants.gov applications. DUNS/SAM.gov required.",
        "website": "https://www.samhsa.gov/grants",
        "notes": "Substance Abuse and Mental Health Services Administration. Crisis services, community mental health, prevention.",
        "source_urls": ["https://www.samhsa.gov/grants/grant-announcements"],
        "source_references": [],
        "source_notes": "SAMHSA grants page",
        "verification_status": "unverified",
    },
    {
        "name": "Mental Health America",
        "funder_type": "other",
        "geography": ["National"],
        "focus_areas": ["Mental Health", "Mental Health Advocacy", "Peer Support"],
        "beneficiaries": ["Adults with mental illness", "Youth", "Communities of color"],
        "eligibility_notes": "MHA affiliate organizations get priority. Affiliate membership opens funding access.",
        "website": "https://www.mhanational.org",
        "notes": "Affiliate network. Orgs affiliated with MHA access technical assistance, training, and some funding.",
        "source_urls": ["https://www.mhanational.org/affiliate-resources"],
        "source_references": [],
        "source_notes": "MHA affiliate page",
        "verification_status": "unverified",
    },
    {
        "name": "Meadows Mental Health Policy Institute",
        "funder_type": "other",
        "geography": ["Texas", "National"],
        "focus_areas": ["Mental Health Policy", "Mental Health Access", "Criminal Justice", "Schools"],
        "beneficiaries": ["Adults with mental illness", "Youth", "Justice-involved individuals"],
        "eligibility_notes": "Texas-primary. Collaborative/policy focus. Contact directly for partnership.",
        "website": "https://mmhpi.org",
        "notes": "Policy-focused. Mental health system reform. School mental health and justice diversion.",
        "source_urls": ["https://mmhpi.org"],
        "source_references": [],
        "source_notes": "MMHPI website",
        "verification_status": "unverified",
    },
    {
        "name": "Behavioral Health Excellence Initiative (Blue Cross Blue Shield)",
        "funder_type": "corporate_foundation",
        "geography": ["National"],
        "focus_areas": ["Mental Health", "Substance Use Disorder", "Behavioral Health Integration"],
        "beneficiaries": ["Adults with mental illness", "Youth", "Underserved communities"],
        "eligibility_notes": "Varies by BCBS affiliate/state. Contact your state's BCBS foundation.",
        "website": "https://www.bcbs.com/the-health-of-america/healthequity",
        "notes": "Each state BCBS affiliate has its own foundation/grant program. Mental health a consistent priority.",
        "source_urls": ["https://www.bcbs.com/the-health-of-america/healthequity"],
        "source_references": [],
        "source_notes": "BCBS health equity",
        "verification_status": "unverified",
    },
]

MENTAL_HEALTH_OPPORTUNITIES = [
    {
        "name": "SAMHSA Certified Community Behavioral Health Clinic (CCBHC) Grant",
        "opportunity_type": "grant",
        "source_type": "government",
        "source_name": "SAMHSA",
        "geography": ["National"],
        "focus_areas": ["Mental Health", "Substance Use Disorder", "Community Behavioral Health"],
        "beneficiaries": ["Adults with mental illness", "Individuals with substance use disorders"],
        "eligibility_notes": "Must be or become CCBHC certified. Multi-year funding.",
        "funding_amount": 1000000,
        "deadline": None,
        "priority_level": "high",
        "status": "active",
        "notes": "Transformative funding for community mental health centers. Requires CCBHC certification.",
        "source_urls": ["https://www.samhsa.gov/grants/grant-announcements"],
        "source_references": [],
        "source_notes": "SAMHSA grants",
        "verification_status": "unverified",
    },
]

# ── Immigration & Refugee Services ───────────────────────────────────────────

IMMIGRATION_FUNDERS = [
    {
        "name": "Office of Refugee Resettlement (ORR)",
        "funder_type": "federal_government",
        "geography": ["National"],
        "focus_areas": ["Refugee Resettlement", "Asylee Support", "Immigration Legal Services"],
        "beneficiaries": ["Refugees", "Asylees", "Unaccompanied minors", "Immigrants"],
        "eligibility_notes": "Must be a state-designated resettlement agency or partner. State matching requirements.",
        "website": "https://www.acf.hhs.gov/orr",
        "notes": "Primary federal funder for refugee services. Works through state resettlement networks.",
        "source_urls": ["https://www.acf.hhs.gov/orr/grant-funding"],
        "source_references": [],
        "source_notes": "ORR grants page",
        "verification_status": "unverified",
    },
    {
        "name": "International Rescue Committee",
        "funder_type": "other",
        "geography": ["National"],
        "focus_areas": ["Refugee Resettlement", "Immigration", "Workforce Development", "Health"],
        "beneficiaries": ["Refugees", "Asylees", "Immigrants"],
        "eligibility_notes": "IRC affiliate organizations. Subaward opportunities through IRC field offices.",
        "website": "https://www.rescue.org",
        "notes": "Subaward opportunities through IRC's 20+ US offices. Contact local IRC office.",
        "source_urls": ["https://www.rescue.org/"],
        "source_references": [],
        "source_notes": "IRC website",
        "verification_status": "unverified",
    },
    {
        "name": "National Immigration Law Center (NILC) Immigrant Justice Fund",
        "funder_type": "other",
        "geography": ["National"],
        "focus_areas": ["Immigration Legal Services", "Policy Advocacy", "Immigrant Rights"],
        "beneficiaries": ["Low-income immigrants", "Undocumented individuals", "DACA recipients"],
        "eligibility_notes": "Legal aid organizations and advocacy groups. LOI required.",
        "website": "https://www.nilc.org",
        "notes": "Legal services and policy advocacy for immigrants. Movement-building focus.",
        "source_urls": ["https://www.nilc.org/"],
        "source_references": [],
        "source_notes": "NILC website",
        "verification_status": "unverified",
    },
    {
        "name": "USCIS Citizenship and Integration Grant Program",
        "funder_type": "federal_government",
        "geography": ["National"],
        "focus_areas": ["Citizenship", "Civic Integration", "Immigration Services", "English Language"],
        "beneficiaries": ["Legal permanent residents", "Immigrants"],
        "eligibility_notes": "501(c)(3) required. USCIS grants for citizenship prep and integration programs.",
        "website": "https://www.uscis.gov/citizenship/organizations/citizenship-and-integration-grants",
        "notes": "Annual competitive grants for citizenship preparation and new immigrant integration.",
        "source_urls": ["https://www.uscis.gov/citizenship/organizations/citizenship-and-integration-grants"],
        "source_references": [],
        "source_notes": "USCIS grants page",
        "verification_status": "unverified",
    },
]

IMMIGRATION_OPPORTUNITIES = [
    {
        "name": "USCIS Citizenship and Integration Grant",
        "opportunity_type": "grant",
        "source_type": "government",
        "source_name": "USCIS",
        "geography": ["National"],
        "focus_areas": ["Citizenship", "Civic Integration"],
        "beneficiaries": ["Legal permanent residents"],
        "eligibility_notes": "501(c)(3) required. Annual competition.",
        "funding_amount": 350000,
        "deadline": None,
        "priority_level": "high",
        "status": "active",
        "notes": "3-year grants. Competitive. Focus on naturalization preparation and civic integration.",
        "source_urls": ["https://www.uscis.gov/citizenship/organizations/citizenship-and-integration-grants"],
        "source_references": [],
        "source_notes": "USCIS grants",
        "verification_status": "unverified",
    },
]

# ── Early Childhood & Family Support ─────────────────────────────────────────

EARLY_CHILDHOOD_FUNDERS = [
    {
        "name": "HHS Early Head Start / Head Start",
        "funder_type": "federal_government",
        "geography": ["National"],
        "focus_areas": ["Early Childhood", "Child Development", "Family Support", "School Readiness"],
        "beneficiaries": ["Children ages 0-5", "Families", "Pregnant women", "Low-income families"],
        "eligibility_notes": "501(c)(3) or government. Competitive grants via Grants.gov. SAM.gov required.",
        "website": "https://www.acf.hhs.gov/ohs",
        "notes": "Flagship federal early childhood program. Multi-year grants, significant.",
        "source_urls": ["https://www.acf.hhs.gov/ohs/funding"],
        "source_references": [],
        "source_notes": "Head Start grants page",
        "verification_status": "unverified",
    },
    {
        "name": "David & Lucile Packard Foundation",
        "funder_type": "family_foundation",
        "geography": ["National", "California"],
        "focus_areas": ["Early Childhood", "Child Development", "Children's Health", "Conservation"],
        "beneficiaries": ["Children ages 0-5", "Families", "Low-income families"],
        "eligibility_notes": "Invitation-based primarily. California orgs can request consideration.",
        "website": "https://www.packard.org",
        "notes": "Major early childhood funder. Children, Families, and Communities program.",
        "source_urls": ["https://www.packard.org/grants/"],
        "source_references": [],
        "source_notes": "Packard Foundation grants",
        "verification_status": "unverified",
    },
    {
        "name": "Zero to Three",
        "funder_type": "other",
        "geography": ["National"],
        "focus_areas": ["Early Childhood", "Infant Mental Health", "Family Support", "Child Development"],
        "beneficiaries": ["Children ages 0-3", "Families", "Early childhood professionals"],
        "eligibility_notes": "Subaward opportunities through federal projects. Contact directly.",
        "website": "https://www.zerotothree.org",
        "notes": "Training, technical assistance, and some subaward funding for early childhood programs.",
        "source_urls": ["https://www.zerotothree.org"],
        "source_references": [],
        "source_notes": "Zero to Three website",
        "verification_status": "unverified",
    },
    {
        "name": "Bezos Family Foundation",
        "funder_type": "family_foundation",
        "geography": ["National"],
        "focus_areas": ["Early Childhood", "Education", "Youth Development", "Leadership"],
        "beneficiaries": ["Children", "Youth", "Educators"],
        "eligibility_notes": "Invitation-based. Vroom program open to partner orgs. Contact for partnership.",
        "website": "https://www.bezosfamilyfoundation.org",
        "notes": "Vroom initiative: brain-building tips for parents. Partnership model.",
        "source_urls": ["https://www.bezosfamilyfoundation.org/"],
        "source_references": [],
        "source_notes": "Bezos Family Foundation",
        "verification_status": "unverified",
    },
]

EARLY_CHILDHOOD_OPPORTUNITIES = [
    {
        "name": "Child Care and Development Fund (CCDF) State Grants",
        "opportunity_type": "grant",
        "source_type": "government",
        "source_name": "HHS / State Child Care Agency",
        "geography": ["State"],
        "focus_areas": ["Early Childhood", "Child Care", "Family Support"],
        "beneficiaries": ["Children ages 0-13", "Low-income families"],
        "eligibility_notes": "Apply through your state child care agency. Licensed child care providers.",
        "funding_amount": 150000,
        "deadline": None,
        "priority_level": "high",
        "status": "active",
        "notes": "State-distributed federal funds for child care subsidies and quality improvement.",
        "source_urls": ["https://www.acf.hhs.gov/occ/ccdf-fundamentals"],
        "source_references": [],
        "source_notes": "HHS Office of Child Care",
        "verification_status": "unverified",
    },
]

# ── Universal partners (broadly applicable) ───────────────────────────────────

UNIVERSAL_PARTNERS = [
    {
        "name": "United Way (local affiliate)",
        "partner_type": "community_based_organization",
        "geography": ["Local"],
        "focus_areas": ["Education", "Health", "Financial Stability", "Basic Needs"],
        "beneficiaries": ["Low-income individuals", "Families", "Children"],
        "collaboration_opportunities": ["Joint funding applications", "Referral network", "Community needs assessment", "Collective impact initiatives"],
        "website": "https://www.unitedway.org/find-your-united-way",
        "notes": "Local United Way affiliates fund and partner with nonprofits in their communities. Huge referral network.",
        "mission_alignment_notes": "United Way is a natural partner for any human services nonprofit — they fund many sectors and connect orgs to community resources.",
        "opportunity_notes": "Join local initiatives, apply for community impact grants, and tap their volunteer/donor network.",
        "source_urls": ["https://www.unitedway.org"],
        "source_references": [],
        "verification_status": "unverified",
    },
    {
        "name": "Local Community Foundation",
        "partner_type": "foundation",
        "geography": ["Local"],
        "focus_areas": ["Community Development", "Education", "Health", "Arts", "Human Services"],
        "beneficiaries": ["Local residents", "Underserved communities"],
        "collaboration_opportunities": ["Competitive grants", "Donor-advised fund referrals", "Capacity building", "Fiscal sponsorship"],
        "website": "https://www.cof.org/page/community-foundation-finder",
        "notes": "Every major metro has a community foundation. They fund local nonprofits across all sectors.",
        "mission_alignment_notes": "Community foundations are the most accessible and flexible local funders for nonprofits of all types.",
        "opportunity_notes": "Apply for competitive grant cycles. Build a relationship with program officers.",
        "source_urls": ["https://www.cof.org/page/community-foundation-finder"],
        "source_references": [],
        "verification_status": "unverified",
    },
    {
        "name": "AmeriCorps (CNCS)",
        "partner_type": "community_based_organization",
        "geography": ["National"],
        "focus_areas": ["Volunteer Programs", "National Service", "Capacity Building"],
        "beneficiaries": ["Nonprofits", "Communities", "Youth"],
        "collaboration_opportunities": ["AmeriCorps member placement", "Capacity building", "Project support", "VISTA volunteers"],
        "website": "https://www.americorps.gov",
        "notes": "AmeriCorps State & National and VISTA programs place members at nonprofits.",
        "mission_alignment_notes": "AmeriCorps members provide staffing capacity at low cost. VISTA members focus on organizational capacity.",
        "opportunity_notes": "Apply for AmeriCorps member slots to expand program delivery without adding full-time staff.",
        "source_urls": ["https://www.americorps.gov/partner"],
        "source_references": [],
        "verification_status": "unverified",
    },
]


def run():
    print("Seeding diverse funder/partner/opportunity data for Anansi Atlas...")

    all_funders = (
        UNIVERSAL_FUNDERS
        + YOUTH_ARTS_FUNDERS
        + HOUSING_FUNDERS
        + FOOD_SECURITY_FUNDERS
        + MENTAL_HEALTH_FUNDERS
        + IMMIGRATION_FUNDERS
        + EARLY_CHILDHOOD_FUNDERS
    )

    all_partners = UNIVERSAL_PARTNERS

    all_opportunities = (
        YOUTH_ARTS_OPPORTUNITIES
        + HOUSING_OPPORTUNITIES
        + FOOD_SECURITY_OPPORTUNITIES
        + MENTAL_HEALTH_OPPORTUNITIES
        + IMMIGRATION_OPPORTUNITIES
        + EARLY_CHILDHOOD_OPPORTUNITIES
    )

    data = {
        "funders": all_funders,
        "partners": all_partners,
        "government_entities": [],
        "resource_providers": [],
        "opportunities": all_opportunities,
    }

    counts = import_research_data(data)

    print(f"\n✅ Seed complete:")
    print(f"   Funders:       {counts['funders']}")
    print(f"   Partners:      {counts['partners']}")
    print(f"   Opportunities: {counts['opportunities']}")
    print(f"\nTotal funders in DB now:")

    from openoutreach.funding.models import Funder
    print(f"   {Funder.objects.count()} funders")


if __name__ == "__main__":
    run()
