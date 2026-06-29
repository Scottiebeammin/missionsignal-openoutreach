"""
Seed: Nonprofit ED Cold Outreach Campaign

Creates a LinkedIn automation Campaign targeting nonprofit Executive Directors
matching the Anansi Atlas ICP (budget $250K–$5M, growth-stage, US-based).

Covers the highest-PMF sectors from the sales skill:
  Workforce Development, Youth Development, Housing, Mental Health,
  Education, Reentry/Justice, Arts & Culture, Digital Equity,
  Environmental Justice, Immigrants & Refugees

Run:
  DEBUG=true .venv/bin/python seeds/seed_nonprofit_campaign.py
  DEBUG=true .venv/bin/python seeds/seed_nonprofit_campaign.py --reset
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "openoutreach.settings")
import django; django.setup()

import argparse
from openoutreach.core.models import Campaign
from openoutreach.linkedin.models import SearchKeyword

CAMPAIGN_NAME = "Anansi Atlas — Nonprofit ED Cold Outreach"

PRODUCT_DOCS = """
Anansi Atlas is a nonprofit opportunity intelligence platform. It delivers an Opportunity Web Snapshot:
a consulting-grade intelligence brief that maps the full ecosystem of aligned funders, strategic partners,
government pathways, and funding readiness gaps around a nonprofit's specific mission — with a 30-day action plan.

Founding partner price: $150/month, locked for life. Includes a personal 45-minute walkthrough call with the team.
Standard price after founding cohort: $299/month.

Intake: https://anansiatlas.com/pilot/
Landing: https://anansiatlas.com/anansi-atlas/
""".strip()

CAMPAIGN_OBJECTIVE = """
Connect with and qualify nonprofit Executive Directors, Development Directors, and Program Directors
at growth-stage nonprofits ($250K–$5M budget) in the United States.

ICP signals to look for:
- Titles: Executive Director, ED, Development Director, Program Director, Co-Founder
- Org size: small to mid (5–50 staff)
- Stage: growth, actively hiring or expanding programs
- Sectors: Workforce Development, Youth Development, Housing & Homelessness, Mental Health,
  Education, Reentry/Justice-Involved, Arts & Culture, Digital Equity, Environmental Justice,
  Immigrants & Refugees, Community Development

Disqualify:
- Universities, hospitals, large national charities (United Way, Red Cross, etc.)
- Consultants, grant writers, or capacity builders (they are potential affiliates, not clients)
- For-profit social enterprises without 501(c)(3) status
- Orgs with in-house development teams of 5+ (they have capacity already)

Connection message angle: Reference their specific work or a sector challenge. Do not pitch immediately.
Follow-up angle (after connection): Map their org to the Anansi Atlas value prop. Offer the Snapshot.
""".strip()

# LinkedIn search strings — these are run one at a time by the daemon
SEARCH_KEYWORDS = [
    # Workforce Development
    'executive director workforce development nonprofit',
    'executive director "workforce board" nonprofit',
    'executive director "job training" nonprofit',
    'executive director "career center" nonprofit',
    'development director workforce nonprofit',

    # Youth Development
    'executive director "youth development" nonprofit',
    'executive director "after school" nonprofit',
    'executive director "youth program" nonprofit',
    'executive director mentorship nonprofit',
    'executive director "boys and girls" nonprofit',

    # Housing & Homelessness
    'executive director "affordable housing" nonprofit',
    'executive director homelessness nonprofit',
    'executive director "housing authority" nonprofit',
    'executive director "continuum of care" nonprofit',

    # Mental Health
    'executive director "mental health" nonprofit',
    'executive director "behavioral health" nonprofit',
    'executive director "community mental health" nonprofit',

    # Education
    'executive director "community school" nonprofit',
    'executive director literacy nonprofit',
    'executive director "early childhood" nonprofit',
    'executive director "adult education" nonprofit',

    # Reentry / Justice
    'executive director reentry nonprofit',
    'executive director "second chance" nonprofit',
    'executive director "justice-involved" nonprofit',
    'executive director "formerly incarcerated" nonprofit',

    # Arts & Culture
    'executive director "arts organization" nonprofit',
    'executive director "cultural organization" nonprofit',
    'executive director "community arts" nonprofit',

    # Digital Equity
    'executive director "digital equity" nonprofit',
    'executive director "digital inclusion" nonprofit',
    'executive director "broadband access" nonprofit',

    # Environmental Justice
    'executive director "environmental justice" nonprofit',
    'executive director "environmental health" nonprofit',

    # Immigrants & Refugees
    'executive director "immigrant services" nonprofit',
    'executive director "refugee resettlement" nonprofit',
    'executive director "immigrant rights" nonprofit',

    # Community Development / General
    'executive director "community development" nonprofit',
    'executive director "community foundation" nonprofit',
    'executive director "social services" nonprofit',
    'executive director "capacity building" nonprofit',
    '"development director" "nonprofit" "executive director"',

    # By geography (high-density nonprofit markets)
    'executive director nonprofit Chicago',
    'executive director nonprofit "Los Angeles"',
    'executive director nonprofit Atlanta',
    'executive director nonprofit "New York"',
    'executive director nonprofit Houston',
    'executive director nonprofit "Washington DC"',
    'executive director nonprofit Detroit',
    'executive director nonprofit "Philadelphia"',
    'executive director nonprofit "San Francisco"',
    'executive director nonprofit "New Orleans"',
    'executive director nonprofit Baltimore',
    'executive director nonprofit "Kansas City"',
    'executive director nonprofit Memphis',
    'executive director nonprofit Cleveland',
    'executive director nonprofit "St. Louis"',
]

parser = argparse.ArgumentParser()
parser.add_argument("--reset", action="store_true", help="Delete and re-seed the campaign")
args = parser.parse_args()

if args.reset:
    deleted, _ = Campaign.objects.filter(name=CAMPAIGN_NAME).delete()
    print(f"Reset: deleted {deleted} campaign(s)")

campaign, created = Campaign.objects.get_or_create(
    name=CAMPAIGN_NAME,
    defaults={
        "product_docs": PRODUCT_DOCS,
        "campaign_objective": CAMPAIGN_OBJECTIVE,
        "booking_link": "https://anansiatlas.com/pilot/",
        "is_freemium": False,
        "action_fraction": 0.15,  # conservative — 15% of discovered profiles get connection requests
    },
)

if not created:
    campaign.product_docs = PRODUCT_DOCS
    campaign.campaign_objective = CAMPAIGN_OBJECTIVE
    campaign.booking_link = "https://anansiatlas.com/pilot/"
    campaign.save(update_fields=["product_docs", "campaign_objective", "booking_link"])
    print(f"Updated existing campaign: {CAMPAIGN_NAME}")
else:
    print(f"Created campaign: {CAMPAIGN_NAME}")

# Add search keywords (skips duplicates)
added = 0
for kw in SEARCH_KEYWORDS:
    _, new = SearchKeyword.objects.get_or_create(campaign=campaign, keyword=kw)
    if new:
        added += 1

total_kw = SearchKeyword.objects.filter(campaign=campaign).count()
print(f"Search keywords: {added} added, {total_kw} total")
print()
print(f"Campaign ID: {campaign.pk}")
print(f"Keywords: {total_kw} search strings queued")
print()
print("Next steps:")
print("  1. Assign the campaign to your account in Django Admin:")
print(f"     http://localhost:8001/admin/core/campaign/{campaign.pk}/change/")
print("  2. Start the daemon: make run")
print("  3. The daemon will work through search keywords and send connection requests")
print("     to qualifying nonprofit EDs automatically.")
print()
print("Tip: Set action_fraction lower (0.05) to be more selective,")
print("     or higher (0.25) to connect more aggressively.")
