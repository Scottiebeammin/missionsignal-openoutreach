"""
Seed / refresh the Tech Sassy Girlz demo workspace.

Profile is built from their own public website (techsassygirlz.org) plus the
IRS 990 filing for their legal entity — mission, programs, who they serve,
geography, real named partners — so a live demo shows real funders matched to
their real mission. Safe: upserts the org by name and never touches global
reference tables (Funder / 990-PF data / other tenants).

    python manage.py seed_tech_sassy_girlz
"""
from django.core.management.base import BaseCommand

from openoutreach.core.models import Organization, Project

NAME = "Tech Sassy Girlz"


class Command(BaseCommand):
    help = "Seed/refresh the Tech Sassy Girlz demo workspace (profile sourced from techsassygirlz.org)."

    def handle(self, *args, **options):
        org = Organization.objects.filter(name__icontains="Tech Sassy Girlz").order_by("pk").first()
        if org is None:
            org = Organization(name=NAME)

        org.name = NAME
        org.website = "https://techsassygirlz.org"
        # Verbatim from their site.
        org.mission = (
            "Tech Sassy Girlz is building the future workforce by transforming the lives of "
            "adolescent girls to pursue science, technology, engineering, and mathematics (STEM) "
            "fields through career readiness, mentoring and entrepreneurship."
        )
        org.organization_summary = (
            "Tech Sassy Girlz is the signature program of Collegiate Pathways, Inc., an Orlando "
            "501(c)(3) (EIN 38-3871171). Founded in 2012 by Dr. Laine Powell to address the "
            "shortage of women and minorities in high-tech careers, it moves underrepresented "
            "girls in grades 6-12 along a STEM pathway: an after-school coding program, an "
            "accelerator for high school juniors and seniors that ends in placed internships, "
            "industry site visits with women role models in STEM, and an annual conference hosted "
            "at UCF. Delivery runs through school and university partners rather than owned "
            "facilities, and corporate STEM employers supply the mentors, tours, and internships."
        )
        org.organization_type = "Nonprofit"
        org.legal_structure = "501(c)(3)"
        org.nonprofit_status = "501(c)(3)"
        # The brand is Tech Sassy Girlz; the filer of record is Collegiate Pathways, Inc.
        # Grant applications and 990 lookups use the legal name.
        org.aliases = ["Collegiate Pathways, Inc.", "Collegiate Pathways Inc", "TSG"]
        org.city = "Orlando"
        org.state = "Florida"
        org.county = "Orange"
        org.headquarters_location = "Orlando, FL"
        # Programming is Orlando-anchored (UCF, Valencia, OCPS) but they describe
        # their reach as middle and high school girls throughout Florida.
        org.service_geographies = ["Orlando", "Orange County", "Central Florida", "Florida"]
        # These double as the Grants.gov keyword query (see pull_grants_gov), so the
        # mix decides what lands on her board. Weighted toward the out-of-school-time
        # and workforce lanes a community nonprofit can actually prime — the pure
        # research phrasings ("computer science education") pull NSF programs that
        # only a degree-granting institution can lead.
        org.focus_areas = [
            "youth development", "after-school programs", "workforce development",
            "STEAM education", "STEM education", "girls empowerment",
            "career readiness", "mentorship", "entrepreneurship",
            "workforce pathways", "college access", "scholarships",
        ]
        org.beneficiaries = [
            "middle school girls", "high school girls", "girls in grades 6-12",
            "underrepresented girls in STEM", "girls of color", "underserved youth",
        ]
        org.capabilities = [
            "after-school coding instruction (Tech Sassy Girlz Code)",
            "college and career accelerator for high school juniors and seniors (Pearls in Tech)",
            "internship placement with corporate STEM employers",
            "industry site visits with women STEM role models (Tech Treks)",
            "annual STEM conference delivery at a university campus",
            "mentorship coordination",
            "entrepreneurship and digital skills curriculum",
            "scholarship distribution",
            "corporate and school-district partnership development",
        ]
        org.outcomes_and_impact = [
            "3,000 middle and high school girls served",
            "$20,000 awarded in scholarships",
            "1,200 volunteer hours contributed",
            "30+ girls introduced to STEM fields annually",
            "Annual conference hosted at the University of Central Florida",
            "Accelerator graduates placed into arranged internships",
            "Operating continuously since 2012",
        ]
        # Real, named partners from their site — these are the relationship assets a
        # funder cares about, and the reason their school- and campus-based delivery works.
        org.existing_partnerships = [
            "Orange County Public Schools",
            "University of Central Florida",
            "Valencia College",
            "NBA Foundation",
            "Infosys Foundation USA",
            "Electronic Arts",
            "Lockheed Martin",
            "Oracle",
            "Grow with Google",
        ]
        org.current_funding_sources = [
            "corporate foundation grants", "corporate sponsorships", "donations",
        ]
        # Grounded, not estimated: Collegiate Pathways, Inc. reported $365,300 revenue
        # on its most recent IRS filing (FY2024, EIN 38-3871171). Value is the token
        # form the "grants your size" sort matches on — see foundations._BUDGET_TARGET.
        org.budget_range = "250k-1m"
        org.analysis_status = "ready"
        org.active = True
        org.save()

        project, created = Project.objects.get_or_create(organization=org, defaults={"name": org.name})

        # Program Readiness scores off project.programs, not the org summary — leaving
        # it empty scores 25 and reports "Programs need clearer definition" to a client
        # whose site lists six of them. website_verification also splits this field on
        # "·" to build the claims it checks against the live site, so the separator
        # matters as much as the content.
        project.programs = (
            "Tech Sassy Girlz Code · Pearls in Tech Accelerator · Tech Treks · "
            "Tech Sassy Girlz Annual Conference · Tech Your Impact · Grow with Google"
        )
        project.program_summaries = [
            {"name": "Tech Sassy Girlz Code",
             "description": "After-school coding program building the pipeline of underrepresented girls into STEM fields through hands-on learning."},
            {"name": "Pearls in Tech Accelerator",
             "description": "Accelerator for high school juniors and seniors building 21st-century digital and technical skills; graduates move into internships the organization arranges."},
            {"name": "Tech Treks",
             "description": "Hands-on industry tours where girls meet women role models in STEM, including simulations and career discussions."},
            {"name": "Tech Sassy Girlz Annual Conference",
             "description": "Annual conference hosted at the University of Central Florida — campus tours, demonstrations, engineering challenges and career exploration."},
            {"name": "Tech Your Impact",
             "description": "Program engaging girls in applying technology to community impact."},
            {"name": "Grow with Google",
             "description": "Google-partnered digital skills training delivered to program participants."},
        ]
        project.save()

        self.stdout.write(self.style.SUCCESS(
            f"{'Created' if created else 'Refreshed'} Tech Sassy Girlz workspace — org #{org.pk}, project #{project.pk}.\n"
            f"  Client view: /projects/{project.pk}/dashboard/\n"
            f"  Foundations (the receipts): /projects/{project.pk}/foundations/"
        ))
