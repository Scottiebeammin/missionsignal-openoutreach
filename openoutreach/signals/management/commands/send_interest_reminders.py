"""
Management command: send_interest_reminders

Weekly reminder to each project owner of the opportunities they're TRACKING
(`is_interested=True`) and haven't applied to yet. Reminders stop automatically once
the org marks an opportunity applied/submitted/won or un-tracks it (is_interested=False).

Exits non-zero when every attempted send failed, so a broken transport surfaces
as a failed cron run rather than a green one. This job silently sent nothing from
the day it was created until 2026-08-29 because its Render service carries no
EMAIL_* variables; a green run must never mean that again.

Run weekly (Render cron):
  python manage.py send_interest_reminders
  python manage.py send_interest_reminders --dry-run
"""
from datetime import date

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Email project owners a weekly reminder of their tracked (interested) opportunities."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Print what would send; no emails")

    def handle(self, *args, **options):
        from openoutreach.core.models import Project
        from openoutreach.funding.models import Opportunity
        from openoutreach.signals.notifications import send_interest_reminder

        today = date.today()
        dry = options["dry_run"]
        sent = 0
        failed = 0

        for project in Project.objects.filter(active=True).select_related("organization"):
            owners = [u for u in project.users.all() if u.email]
            if not owners:
                continue
            tracked = (
                Opportunity.objects.filter(project=project, is_interested=True)
                .order_by("deadline", "name")
            )
            items = []
            for opp in tracked:
                if opp.is_applied:  # applied/submitted/won/terminal — stop reminding
                    continue
                days = (opp.deadline - today).days if opp.deadline else None
                items.append((opp, days))

            if not items:
                continue

            label = f"{project.organization.name}: {len(items)} tracked"
            for owner in owners:
                if dry:
                    self.stdout.write(f"  [dry] -> {owner.email} | {label}")
                elif send_interest_reminder(owner, project, items):
                    sent += 1
                    self.stdout.write(self.style.SUCCESS(f"  sent -> {owner.email} | {label}"))
                else:
                    failed += 1
                    self.stdout.write(self.style.ERROR(f"  FAILED -> {owner.email} | {label}"))

        if dry:
            self.stdout.write(self.style.WARNING("\nDry run — no emails sent."))
            return

        self.stdout.write(f"\nDone. Sent: {sent}  Failed: {failed}")
        if failed and not sent:
            raise CommandError(
                f"Every reminder send failed ({failed} attempted, 0 delivered). "
                "This is a transport failure, not a data problem — check the EMAIL_* "
                "environment variables on this service."
            )
        if failed:
            self.stdout.write(self.style.WARNING(
                f"{failed} send(s) failed but {sent} succeeded — see the log."
            ))
