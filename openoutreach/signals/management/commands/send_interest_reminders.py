"""
Management command: send_interest_reminders

Weekly reminder to each project owner of the opportunities they're TRACKING
(`is_interested=True`) and haven't applied to yet. Reminders stop automatically once
the org marks an opportunity applied/submitted/won or un-tracks it (is_interested=False).

Run weekly (Render cron):
  python manage.py send_interest_reminders
  python manage.py send_interest_reminders --dry-run
"""
from datetime import date

from django.core.management.base import BaseCommand


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

        if dry:
            self.stdout.write(self.style.WARNING("\nDry run — no emails sent."))
        else:
            self.stdout.write(self.style.SUCCESS(f"\nDone. {sent} reminder email(s) sent."))
