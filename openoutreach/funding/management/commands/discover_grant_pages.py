"""
Management command: discover_grant_pages

Layer 2 grounded discovery: fetch funder websites (stdlib HTTP), find their
grant pages deterministically, then use the LLM only to EXTRACT programs
explicitly described in the fetched text. Everything persists through the
grounding gate, so every saved Opportunity points at a page this process
actually downloaded.

Usage:
  python manage.py discover_grant_pages --project-id 1
  python manage.py discover_grant_pages --project-id 1 --max-funders 5
  python manage.py discover_grant_pages --project-id 1 --dry-run
"""
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Grounded fetch-then-extract discovery of foundation grant programs."

    def add_arguments(self, parser):
        parser.add_argument("--project-id", type=int, required=True, help="Project to discover for")
        parser.add_argument("--max-funders", type=int, default=15, help="Max funders to scan (default 15)")
        parser.add_argument("--max-pages", type=int, default=3,
                            help="Max grant sub-pages fetched per funder (default 3)")
        parser.add_argument("--dry-run", action="store_true",
                            help="Print extracted programs without persisting")

    def handle(self, *args, **options):
        from openoutreach.core.models import Project
        from openoutreach.funding.web_discovery import discover_for_project

        try:
            project = Project.objects.get(pk=options["project_id"])
        except Project.DoesNotExist:
            raise CommandError(f"Project {options['project_id']} not found")

        dry = options["dry_run"]
        report = discover_for_project(
            project,
            max_funders=options["max_funders"],
            max_pages_per_funder=options["max_pages"],
            dry_run=dry,
        )

        org_name = getattr(project.organization, "name", f"Project {project.pk}")
        self.stdout.write(f"\nGrounded web discovery — {org_name}")

        if report.skipped_llm_unavailable:
            self.stdout.write(self.style.WARNING(
                "LLM not configured — the extraction step needs a model. "
                "Set LLM_PROVIDER / LLM_API_KEY / AI_MODEL in Django Admin "
                "(/admin/core/siteconfig/) and re-run."
            ))

        self.stdout.write(f"  Funders scanned:    {report.funders_scanned}")
        self.stdout.write(f"  Pages fetched:      {report.pages_fetched}")
        self.stdout.write(f"  Programs extracted: {report.programs_extracted}")
        self.stdout.write(f"  Saved (gate-passed): {report.saved}")
        self.stdout.write(f"  Rejected by gate:   {report.rejected}")
        for line in report.lines:
            self.stdout.write(f"    {line}")

        if dry:
            self.stdout.write(self.style.WARNING("\nDry run — nothing written."))
            for c in report.candidates:
                deadline = c["deadline"].isoformat() if c.get("deadline") else "none"
                self.stdout.write(f"  - {c['name']}  [{c['source_url']}]  deadline: {deadline}")
                if c.get("description"):
                    self.stdout.write(f"      {c['description'][:200]}")
        elif not report.skipped_llm_unavailable:
            self.stdout.write(self.style.SUCCESS(
                "\nDone. Saved rows are needs_review — every source_url is a page "
                "this run actually fetched."
            ))
