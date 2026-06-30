"""
Management command: pull_grants_gov

Pull live federal grant opportunities from the public Grants.gov API into a
project's Opportunity pipeline. Every row created is verified (real grants.gov
URL + real close date) — zero hallucination.

Usage:
  python manage.py pull_grants_gov --project-id 1
  python manage.py pull_grants_gov --project-id 1 --keywords "youth workforce,after school"
  python manage.py pull_grants_gov --all --rows 15
  python manage.py pull_grants_gov --project-id 1 --dry-run
"""
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Pull live federal grants from Grants.gov into project Opportunities."

    def add_arguments(self, parser):
        parser.add_argument("--project-id", type=int, default=0, help="Project to ingest grants for")
        parser.add_argument("--all", action="store_true", help="Ingest for every active project")
        parser.add_argument("--keywords", default="", help="Comma-separated keyword override")
        parser.add_argument("--rows", type=int, default=25, help="Max hits per keyword (default 25)")
        parser.add_argument("--dry-run", action="store_true", help="Report counts without writing")

    def handle(self, *args, **options):
        from openoutreach.core.models import Project
        from openoutreach.funding.grants_gov import ingest_grants_for_project

        if options["all"]:
            projects = list(Project.objects.filter(active=True))
        elif options["project_id"]:
            try:
                projects = [Project.objects.get(pk=options["project_id"])]
            except Project.DoesNotExist:
                raise CommandError(f"Project {options['project_id']} not found")
        else:
            raise CommandError("Pass --project-id <id> or --all")

        keywords = [k.strip() for k in options["keywords"].split(",") if k.strip()] or None
        dry = options["dry_run"]

        for project in projects:
            org_name = getattr(project.organization, "name", f"Project {project.pk}")
            result = ingest_grants_for_project(
                project, keywords, rows_per_keyword=options["rows"], dry_run=dry
            )
            verb = "would create" if dry else "created"
            self.stdout.write(
                f"\n{org_name}: {verb} {result['created']}, updated {result['updated']}, "
                f"skipped {result['skipped']}"
            )
            self.stdout.write(f"  keywords: {', '.join(result['keywords']) or '(none)'}")
            for err in result["errors"]:
                self.stdout.write(self.style.WARNING(f"  ! {err}"))

        if dry:
            self.stdout.write(self.style.WARNING("\nDry run — nothing written."))
        else:
            self.stdout.write(self.style.SUCCESS("\nDone. Verified federal grants ingested."))
