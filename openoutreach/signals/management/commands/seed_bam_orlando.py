"""
Seed / refresh the Black Architects in the Making (BAM) Orlando demo workspace.

Profile is built from their own public website (bamorlando.org) — mission,
programs, who they serve, geography — so a live demo shows real funders matched
to their real mission. Safe: upserts the org by name and never touches global
reference tables (Funder / 990-PF data / other tenants).

    python manage.py seed_bam_orlando
"""
from django.core.management.base import BaseCommand

from openoutreach.core.models import Organization, Project

NAME = "Black Architects in the Making (BAM) Orlando"


class Command(BaseCommand):
    help = "Seed/refresh the BAM Orlando demo workspace (profile sourced from bamorlando.org)."

    def handle(self, *args, **options):
        org = Organization.objects.filter(name__icontains="Black Architects").order_by("pk").first()
        if org is None:
            org = Organization(name=NAME)

        org.name = NAME
        org.website = "https://www.bamorlando.org"
        org.mission = (
            "To mobilize architects who are passionate about their craft into communities where Black "
            "families live, learn, and play — engaging students through creative, inspiring, and "
            "hands-on experiences in architecture and design."
        )
        org.organization_summary = (
            "BAM Orlando creates pathways into architecture for Black students through hands-on "
            "workshops, scholarships, internships, and mentorship, while raising awareness of "
            "architecture and design in Black communities across Orlando."
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
            "architecture and design education", "youth development", "education support",
            "mentorship", "career readiness", "arts and culture", "STEM education",
            "racial equity", "scholarships", "workforce pathways",
        ]
        org.beneficiaries = [
            "Black students", "youth", "students of color", "aspiring architects", "underserved youth",
        ]
        org.capabilities = [
            "hands-on architecture and design workshops", "scholarship distribution",
            "internship placement", "mentorship coordination", "community advocacy",
            "volunteer mobilization",
        ]
        org.outcomes_and_impact = [
            "135+ students engaged through hands-on workshops in 2025",
            "14 educational workshops conducted in 2025",
            "$29,480 raised in community donations in 2025",
            "87+ volunteers mobilized",
            "Scholarship and internship pathways into architecture careers",
        ]
        org.budget_range = "under_250k"
        org.analysis_status = "ready"
        org.active = True
        org.save()

        project, created = Project.objects.get_or_create(organization=org, defaults={"name": org.name})

        self.stdout.write(self.style.SUCCESS(
            f"{'Created' if created else 'Refreshed'} BAM Orlando workspace — org #{org.pk}, project #{project.pk}.\n"
            f"  Open the client view at: /projects/{project.pk}/dashboard/\n"
            f"  Foundations (the receipts): /projects/{project.pk}/foundations/"
        ))
