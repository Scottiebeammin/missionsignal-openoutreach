"""
Management command: expire_opportunities

Sweep every project's board for grants whose deadline has passed and that the org
never applied to, and move them to EXPIRED — so a closed grant stops sitting in
front of a client as if it were still open.

The pipeline page already runs this sweep on load, but only for the project being
viewed. Projects nobody opens keep showing dead deadlines, and the alert digest
reads the same rows. Run this daily, after the data refresh:

  python manage.py pull_grants_gov --all && python manage.py expire_opportunities

  python manage.py expire_opportunities --dry-run       # list what would move
  python manage.py expire_opportunities --project 13    # one project only

Applied / won / already-archived rows are never touched: only genuinely-missed
deadlines get swept. Idempotent — a second run moves nothing.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Move past-deadline, never-applied opportunities to EXPIRED across all projects."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="List what would move; change nothing")
        parser.add_argument("--project", type=int, default=None, help="Limit to one project id")

    def handle(self, *args, **options):
        from openoutreach.core.models import Project
        from openoutreach.signals.lifecycle import (
            expire_past_deadline_opportunities,
            past_deadline_opportunities,
        )

        project = None
        if options["project"] is not None:
            project = Project.objects.filter(pk=options["project"]).first()
            if project is None:
                self.stderr.write(self.style.ERROR(f"No project with id {options['project']}."))
                return

        stale = past_deadline_opportunities(project).select_related("project").order_by("deadline")
        for opportunity in stale:
            label = opportunity.project.name if opportunity.project_id else "(no project)"
            self.stdout.write(f"  {opportunity.deadline}  [{label}]  {opportunity.name}")

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING(f"Dry run — {len(stale)} opportunity(ies) would be expired."))
            return

        moved = expire_past_deadline_opportunities(project)
        self.stdout.write(self.style.SUCCESS(f"Expired {moved} past-deadline opportunity(ies)."))
