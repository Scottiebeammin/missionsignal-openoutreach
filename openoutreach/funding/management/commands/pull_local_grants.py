"""
Management command: pull_local_grants

Ingest state, county and city funding sources — the layer Grants.gov cannot see.
Sources are matched to each organization's own geography, fetched live, and
persisted through the grounding gate, so every saved row points at a page this
process actually downloaded.

Usage:
  python manage.py pull_local_grants --project-id 3
  python manage.py pull_local_grants --all
  python manage.py pull_local_grants --project-id 3 --dry-run
  python manage.py pull_local_grants --list-sources
"""
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Ingest state/county/city funding sources for a project (or every active project)."

    def add_arguments(self, parser):
        parser.add_argument("--project-id", type=int, default=0, help="Project to ingest for")
        parser.add_argument("--all", action="store_true", help="Every active project")
        parser.add_argument("--dry-run", action="store_true",
                            help="Fetch and report without writing anything")
        parser.add_argument("--list-sources", action="store_true",
                            help="Print the source registry and exit")

    def handle(self, *args, **options):
        from openoutreach.core.models import Project
        from openoutreach.funding.local_sources import (
            LOCAL_SOURCES, discover_local_for_project, sources_for_organization,
        )

        if options["list_sources"]:
            self.stdout.write(f"{len(LOCAL_SOURCES)} registered source(s):")
            for s in LOCAL_SOURCES:
                scope = " / ".join(p for p in (s.state, s.county, s.city) if p)
                flag = self.style.ERROR(" [BLOCKED]") if s.is_blocked else ""
                self.stdout.write(f"  {s.key:<28} {s.level:<7} {scope}{flag}")
                self.stdout.write(f"      {s.url}")
                if s.is_blocked:
                    self.stdout.write(self.style.WARNING(f"      reason: {s.blocked}"))
            return

        if options["all"]:
            projects = list(Project.objects.select_related("organization").filter(organization__active=True))
        elif options["project_id"]:
            try:
                projects = [Project.objects.select_related("organization").get(pk=options["project_id"])]
            except Project.DoesNotExist:
                raise CommandError(f"Project {options['project_id']} not found")
        else:
            raise CommandError("Pass --project-id <id> or --all")

        dry = options["dry_run"]
        for project in projects:
            org = project.organization
            self.stdout.write(f"\n{org.name} (project {project.pk})")
            matched = sources_for_organization(org)
            if not matched and not org.state:
                self.stdout.write(self.style.WARNING(
                    "  No state on the organization profile — cannot match any local source."))
                continue

            report = discover_local_for_project(project, dry_run=dry)
            self.stdout.write(
                f"  matched {report.matched} source(s), fetched {report.fetched}, "
                f"extraction={report.extraction}"
            )
            for name in report.unreachable:
                self.stdout.write(self.style.WARNING(f"  unreachable: {name}"))
            for note in report.blocked:
                self.stdout.write(self.style.WARNING(f"  known gap:   {note}"))
            for c in report.candidates:
                deadline = c.get("deadline") or "no stated deadline"
                self.stdout.write(f"    · {c['name'][:78]}  ({deadline})")
            if dry:
                self.stdout.write(self.style.NOTICE(
                    f"  DRY RUN — {len(report.candidates)} candidate(s), nothing written."))
            else:
                self.stdout.write(self.style.SUCCESS(
                    f"  saved {report.saved}, rejected {report.rejected}"))
                for name in report.rejected_names:
                    self.stdout.write(self.style.WARNING(f"    rejected: {name}"))

        self.stdout.write(self.style.SUCCESS("\nDone."))
