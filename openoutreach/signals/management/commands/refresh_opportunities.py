"""
Management command: refresh_opportunities

Re-runs AI opportunity research for all active projects (or a specific one).
Use this to keep grant deadlines and funder data current.

Usage:
  python manage.py refresh_opportunities
  python manage.py refresh_opportunities --project-id 5
  python manage.py refresh_opportunities --stale-only  # skip projects researched in last 7 days
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Re-run AI opportunity research for active projects."

    def add_arguments(self, parser):
        parser.add_argument("--project-id", type=int, help="Refresh a single project by ID")
        parser.add_argument(
            "--stale-only",
            action="store_true",
            help="Only refresh projects with no opportunities (never researched)",
        )

    def handle(self, *args, **options):
        from openoutreach.core.models import Project
        from openoutreach.signals.research import research_project
        from django.db.models import Count

        qs = Project.objects.select_related("organization").filter(organization__active=True)

        if options["project_id"]:
            qs = qs.filter(pk=options["project_id"])
        elif options["stale_only"]:
            qs = qs.annotate(opp_count=Count("opportunity")).filter(opp_count=0)

        projects = list(qs)
        if not projects:
            self.stdout.write("No projects matched.")
            return

        self.stdout.write(f"Refreshing {len(projects)} project(s)...")
        for project in projects:
            self.stdout.write(f"  → {project.organization.name} (pk={project.pk})... ", ending="")
            try:
                counts = research_project(project)
                parts = [f"{v} {k}" for k, v in counts.items() if v]
                self.stdout.write(self.style.SUCCESS(", ".join(parts) or "no new data"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"FAILED: {e}"))

        self.stdout.write(self.style.SUCCESS("Done."))
