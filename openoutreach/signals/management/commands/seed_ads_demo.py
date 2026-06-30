"""
Management command: seed_ads_demo

Create (or refresh) a polished demo nonprofit for ads / demos / screenshots.
It runs the SAME real pipeline a live client gets — so the dashboards look
authentic: real federal grants (Grants.gov), relevance-ranked, plus the shared
funder/resource directory.

Usage:
  python manage.py seed_ads_demo
  python manage.py seed_ads_demo --reset   # delete and rebuild from scratch

Login to view: username 'demo' / password 'demo12345'
"""
from django.core.management.base import BaseCommand

DEMO_ORG_NAME = "Horizon Youth Collective"
DEMO_USER = "demo"
DEMO_PASS = "demo12345"


class Command(BaseCommand):
    help = "Seed a polished demo nonprofit (ads/demo/screenshots) with real pulled data."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete existing demo org and rebuild")

    def handle(self, *args, **options):
        from django.contrib.auth.models import User
        from openoutreach.core.models import Organization, Project
        from openoutreach.signals.services import create_organization_intake
        from openoutreach.signals.analysis_service import analyze_project
        from openoutreach.funding.grants_gov import ingest_grants_for_project

        if options["reset"]:
            Organization.objects.filter(name=DEMO_ORG_NAME).delete()
            self.stdout.write("Deleted existing demo org.")

        user, _ = User.objects.get_or_create(username=DEMO_USER, defaults={"is_staff": False})
        user.set_password(DEMO_PASS)
        user.email = "demo@anansiatlas.com"
        user.save()

        existing = Organization.objects.filter(name=DEMO_ORG_NAME).first()
        if existing:
            project = Project.objects.filter(organization=existing).first()
            project.users.add(user)
            self.stdout.write(self.style.WARNING(f"Demo org already exists (project {project.pk}). Use --reset to rebuild."))
        else:
            project = create_organization_intake(
                user=user,
                contact_name="Jordan Rivera",
                contact_position="Executive Director",
                contact_email="demo@anansiatlas.com",
                organization_name=DEMO_ORG_NAME,
                website="https://example.org",
                mission=(
                    "Horizon Youth Collective equips underserved youth ages 11-18 in Central "
                    "Florida with mentorship, academic support, career readiness, and life "
                    "skills so they graduate ready for college, work, and leadership."
                ),
                programs=(
                    "After-School Mentorship — weekly 1:1 mentoring and homework support for "
                    "120 students across Orange County.\n\n"
                    "Career Pathways — paid internships, workforce readiness, and employer "
                    "partnerships for high schoolers.\n\n"
                    "Summer Leadership Academy — 6-week college-and-career immersion for "
                    "first-generation students."
                ),
                organization_type="nonprofit",
                city="Orlando",
                county="Orange",
                state="FL",
                service_area_notes="Orange, Osceola, and Seminole counties (Central Florida).",
                budget_range="$250k-$1M",
                focus_area_selections=[
                    "youth development", "mentorship", "career readiness", "education support",
                    "life skills", "workforce development", "college access", "leadership",
                ],
                beneficiary_selections=[
                    "underserved youth", "low-income families", "first-generation students",
                    "minority youth", "teens ages 11-18",
                ],
                intake_notes="Demo organization for Anansi Atlas walkthroughs and ad creation.",
            )
            try:
                analyze_project(project, mode="deterministic")
            except Exception:
                pass
            # Keep geography clean for the demo (analyzer can infer messy values).
            org = project.organization
            org.service_geographies = ["Orlando", "Orange County", "Central Florida"]
            org.save(update_fields=["service_geographies"])
            self.stdout.write(self.style.SUCCESS(f"Created demo org '{DEMO_ORG_NAME}' (project {project.pk})."))

        # Pull real federal grants so the opportunity dashboard looks authentic.
        result = ingest_grants_for_project(project, rows_per_keyword=12)
        self.stdout.write(f"Grants.gov pull: created {result['created']}, updated {result['updated']}.")

        base = "http://localhost:8001"
        self.stdout.write(self.style.SUCCESS("\nDemo ready. Login: demo / demo12345"))
        self.stdout.write(f"  Snapshot:      {base}/projects/{project.pk}/snapshot/")
        self.stdout.write(f"  Opportunities: {base}/projects/{project.pk}/opportunities/")
        self.stdout.write(f"  Resources:     {base}/projects/{project.pk}/resources/")
        self.stdout.write(f"  Dashboard:     {base}/projects/{project.pk}/dashboard/")
