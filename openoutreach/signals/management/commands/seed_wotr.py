"""
Seed / refresh the Women on the Rise International, Inc. (WOTR) workspace.

Profile is built from their own public website (wotrinc.org) — mission,
programs, who they serve, geography, real partners — so a live workspace shows
real funders matched to their real mission. Safe: upserts the org by name and
never touches global reference tables (Funder / 990-PF data / other tenants).

    python manage.py seed_wotr
"""
from django.core.management.base import BaseCommand

from openoutreach.core.models import Organization, Project

NAME = "Women on the Rise International, Inc."


class Command(BaseCommand):
    help = "Seed/refresh the Women on the Rise (WOTR) workspace (profile sourced from wotrinc.org)."

    def handle(self, *args, **options):
        org = Organization.objects.filter(name__icontains="Women on the Rise").order_by("pk").first()
        if org is None:
            org = Organization(name=NAME)

        org.name = NAME
        org.website = "https://www.wotrinc.org"
        org.mission = (
            "Inspiring societies where equality exists in all facets of women's lives."
        )
        org.organization_summary = (
            "Women on the Rise International is an Orlando-based 501(c)(3) that empowers women — "
            "especially those who are underserved and underrepresented — through educational and "
            "motivational programming across four pillars: financial literacy, career development, "
            "entrepreneurship, and personal wellness. Flagship programs include a 10-week Career "
            "Development Cohort, monthly membership meetings with speakers and networking, an annual "
            "Awards Gala, and 'The Rise Society' giving circle. Guiding ethos: 'We compliment. We "
            "don't compete.'"
        )
        org.organization_type = "Nonprofit"
        org.legal_structure = "501(c)(3)"
        org.nonprofit_status = "501(c)(3)"
        org.city = "Orlando"
        org.state = "Florida"
        org.county = "Orange"
        org.headquarters_location = "Orlando, FL"
        org.service_geographies = ["Orlando", "Orange County", "Central Florida", "Florida"]
        org.focus_areas = [
            "women's empowerment", "career development", "financial literacy", "entrepreneurship",
            "economic empowerment", "workforce development", "leadership development",
            "personal wellness", "mentorship", "networking",
        ]
        org.beneficiaries = [
            "women", "underserved women", "underrepresented women", "women entrepreneurs",
            "career-seeking women", "professional women",
        ]
        org.capabilities = [
            "10-week Career Development Cohort", "financial literacy education",
            "entrepreneurship training", "personal wellness programming",
            "monthly membership meetings and networking", "mentorship coordination",
            "annual Awards Gala", "corporate partnership development",
            "The Rise Society giving circle",
        ]
        org.outcomes_and_impact = [
            "Spring 2026 Career Development Cohort completed with multiple graduates celebrated",
            "Recurring monthly membership programming (e.g., 'Ageless Leadership')",
            "The Rise Society giving circle with corporate members (Orlando Health; Block, Inc.)",
            "Multi-tier membership community (Unity, Visionary, Legacy)",
        ]
        # Real, named relationships from their site — the assets a funder cares about.
        org.existing_partnerships = [
            "WholeLife Church",
            "The Greatest Investment (TGI)",
            "Coldwell Banker Realty",
            "Orlando Health",
            "Block, Inc.",
        ]
        org.current_funding_sources = [
            "memberships", "corporate partnerships", "The Rise Society giving circle",
            "donations", "sponsorships",
        ]
        # Estimate — small/mid community nonprofit with corporate giving-circle partners.
        # Refine once WOTR confirms their annual revenue (drives the "grants your size" sort).
        org.budget_range = "under_250k"
        org.analysis_status = "ready"
        org.active = True
        org.save()

        project, created = Project.objects.get_or_create(organization=org, defaults={"name": org.name})

        self.stdout.write(self.style.SUCCESS(
            f"{'Created' if created else 'Refreshed'} WOTR workspace — org #{org.pk}, project #{project.pk}.\n"
            f"  Client view: /projects/{project.pk}/dashboard/\n"
            f"  Foundations (the receipts): /projects/{project.pk}/foundations/"
        ))
