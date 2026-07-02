"""Seed the real free/low-cost capacity-building resource directory.

Idempotent: rows are matched by website domain (so re-running updates in place
instead of duplicating). Every URL here was verified live before inclusion.
Also performs directory hygiene: dedupes TechSoup, deactivates dead-domain rows,
and repoints the Central Florida Foundation funder row at its real domain.
"""

from urllib.parse import urlparse

from django.core.management.base import BaseCommand

from openoutreach.funding.models import Funder, ResourceProvider

FREE = ResourceProvider.ResourceCost.FREE
LOW_COST = ResourceProvider.ResourceCost.LOW_COST
RT = ResourceProvider.ResourceType

# Every URL verified reachable (200/301, or 403 bot-block) before inclusion.
RESOURCES = [
    {
        "name": "Digitunity",
        "website": "https://digitunity.org",
        "resource_type": RT.EQUIPMENT_ASSISTANCE_PROGRAM,
        "cost": FREE,
        "geography": ["National"],
        "resource_categories": ["Technology", "Equipment", "Digital inclusion"],
        "notes": "National nonprofit that connects donated surplus technology (laptops, desktops, tablets) to nonprofits and the communities they serve.",
    },
    {
        "name": "U.S. Small Business Administration (SBA) — Local Assistance",
        "website": "https://www.sba.gov/local-assistance",
        "resource_type": RT.TECHNICAL_ASSISTANCE_PROVIDER,
        "cost": FREE,
        "geography": ["National"],
        "resource_categories": ["Business planning", "Counseling", "Training"],
        "notes": "Free counseling, training, and local resource-partner referrals (SBDCs, Women's Business Centers) for small organizations.",
    },
    {
        "name": "SCORE — Free Business Mentoring",
        "website": "https://www.score.org",
        "resource_type": RT.TECHNICAL_ASSISTANCE_PROVIDER,
        "cost": FREE,
        "geography": ["National"],
        "resource_categories": ["Mentoring", "Workshops"],
        "notes": "Free one-on-one mentoring from experienced business volunteers, plus free and low-cost workshops.",
    },
    {
        "name": "Taproot Foundation",
        "website": "https://taprootfoundation.org",
        "resource_type": RT.VOLUNTEER_NETWORK,
        "cost": FREE,
        "geography": ["National"],
        "resource_categories": ["Pro bono services", "Marketing", "HR", "Strategy", "Technology"],
        "notes": "Connects nonprofits with skilled pro bono professionals for marketing, strategy, HR, IT, and finance projects at no cost.",
    },
    {
        "name": "Catchafire",
        "website": "https://www.catchafire.org",
        "resource_type": RT.VOLUNTEER_NETWORK,
        "cost": FREE,
        "geography": ["National"],
        "resource_categories": ["Pro bono services", "Skills-based volunteering"],
        "notes": "Skills-based volunteer matching platform for nonprofit projects.",
        "eligibility_notes": "Nonprofit access is typically sponsored by a participating funder or community partner at no cost to the nonprofit.",
    },
    {
        "name": "Candid Learning",
        "website": "https://learning.candid.org",
        "resource_type": RT.CAPACITY_BUILDING_ORGANIZATION,
        "cost": FREE,
        "geography": ["National"],
        "resource_categories": ["Fundraising training", "Grant research", "Webinars"],
        "notes": "Free training, webinars, and self-paced courses on fundraising, proposal writing, and nonprofit sustainability from Candid.",
    },
    {
        "name": "Florida Nonprofit Alliance",
        "website": "https://www.floridanonprofits.org",
        "resource_type": RT.NONPROFIT_SUPPORT_CENTER,
        "cost": LOW_COST,
        "geography": ["Florida"],
        "resource_categories": ["Advocacy", "Research", "Training"],
        "notes": "Statewide association for Florida nonprofits: advocacy, sector research, and training. Many resources free; full benefits via low-cost membership.",
    },
    {
        "name": "National Council of Nonprofits",
        "website": "https://www.councilofnonprofits.org",
        "resource_type": RT.NONPROFIT_SUPPORT_CENTER,
        "cost": FREE,
        "geography": ["National"],
        "resource_categories": ["Guides", "Templates", "Policy updates"],
        "notes": "Free practical guides, tools, and policy updates for charitable nonprofits.",
    },
    {
        "name": "Edyth Bush Institute for Philanthropy & Nonprofit Leadership (Rollins College)",
        "website": "https://ebi.rollins.edu",
        "resource_type": RT.UNIVERSITY_PROGRAM,
        "cost": LOW_COST,
        "geography": ["Central Florida", "Orlando"],
        "resource_categories": ["Leadership development", "Board governance", "Training"],
        "notes": "Central Florida's nonprofit leadership center at Rollins College: board governance, leadership, and management workshops at low cost.",
    },
    {
        "name": "Heart of Florida United Way",
        "website": "https://www.hfuw.org",
        "resource_type": RT.CAPACITY_BUILDING_ORGANIZATION,
        "cost": FREE,
        "geography": ["Central Florida", "Orange", "Osceola", "Seminole"],
        "resource_categories": ["Community partnerships", "Volunteer connection", "211 referrals"],
        "notes": "Central Florida's United Way: agency partnerships, volunteer connection, and community resource referrals (211).",
    },
]

# Explicit cost values for pre-existing real rows, keyed by domain.
EXISTING_COSTS = {
    "techsoup.org": LOW_COST,          # admin fees per product
    "google.com": FREE,
    "microsoft.com": FREE,
    "canva.com": FREE,
    "salesforce.org": FREE,            # 10 free licenses via Power of Us
    "pointsoflight.org": FREE,
    "americorps.gov": LOW_COST,        # host sites pay a cost share
    "volunteerflorida.org": LOW_COST,
    "ccie.ucf.edu": LOW_COST,
    "careersourcecentralflorida.com": FREE,
    "unitedartscfl.org": FREE,
    "councilofnonprofits.org": FREE,
    "floridanonprofits.org": LOW_COST,
}

DEAD_DOMAINS = ["nonprofitcenterfl.org"]


def domain_of(url):
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


class Command(BaseCommand):
    help = "Seed/refresh the free & low-cost capacity-building resource directory (idempotent, matched by domain)."

    def handle(self, *args, **options):
        added = updated = 0

        for entry in RESOURCES:
            dom = domain_of(entry["website"])
            existing = [r for r in ResourceProvider.objects.all() if domain_of(r.website) == dom]
            fields = {k: v for k, v in entry.items()}
            if existing:
                row = existing[0]
                for k, v in fields.items():
                    setattr(row, k, v)
                row.active = True
                row.save()
                updated += 1
                self.stdout.write(f"updated: {row.name} ({dom}) cost={row.cost}")
            else:
                row = ResourceProvider.objects.create(active=True, **fields)
                added += 1
                self.stdout.write(f"added:   {row.name} ({dom}) cost={row.cost}")

        # Explicit cost values for pre-existing rows not in RESOURCES.
        cost_set = 0
        for row in ResourceProvider.objects.filter(active=True):
            dom = domain_of(row.website)
            if dom in EXISTING_COSTS and row.cost != EXISTING_COSTS[dom]:
                row.cost = EXISTING_COSTS[dom]
                row.save(update_fields=["cost", "updated_at"])
                cost_set += 1
                self.stdout.write(f"cost:    {row.name} -> {row.cost}")

        # Dedupe by domain: keep the oldest active row per domain, deactivate the rest.
        deduped = 0
        seen = {}
        for row in ResourceProvider.objects.filter(active=True).order_by("id"):
            dom = domain_of(row.website)
            if not dom:
                continue
            if dom in seen:
                row.active = False
                row.save(update_fields=["active", "updated_at"])
                deduped += 1
                self.stdout.write(f"deduped: {row.name} (duplicate of {seen[dom].name}, {dom})")
            else:
                seen[dom] = row

        # Deactivate rows on verified-dead domains.
        deactivated = 0
        for dead in DEAD_DOMAINS:
            for row in ResourceProvider.objects.filter(active=True, website__icontains=dead):
                row.active = False
                row.save(update_fields=["active", "updated_at"])
                deactivated += 1
                self.stdout.write(f"deactivated (dead domain): {row.name} ({dead})")

        # Community Foundation of Central Florida funder row: cffcfl.org is dead;
        # the organization is the Central Florida Foundation at cffound.org (verified).
        repointed = 0
        for funder in Funder.objects.filter(website__icontains="cffcfl.org"):
            funder.name = "Central Florida Foundation"
            funder.website = "https://cffound.org"
            funder.notes = (funder.notes + "\n" if funder.notes else "") + (
                "Domain updated from dead cffcfl.org to verified cffound.org "
                "(organization operates as Central Florida Foundation)."
            )
            funder.save()
            repointed += 1
            self.stdout.write(f"funder repointed: {funder.name} -> https://cffound.org")

        self.stdout.write(self.style.SUCCESS(
            f"Done. added={added} updated={updated} cost_set={cost_set} "
            f"deduped={deduped} deactivated={deactivated} funders_repointed={repointed}"
        ))
