"""
management command: send_nurture_emails

Sends the waitlist nurture sequence (day 1 / day 3 / day 7) to signups
that haven't yet received each email. Safe to run multiple times per day —
uses nurture_step to track position and created_at as the timing anchor.

Usage:
    python manage.py send_nurture_emails           # live send
    python manage.py send_nurture_emails --dry-run # preview only
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from openoutreach.signals.nurture import send_due_nurture_emails


class Command(BaseCommand):
    help = "Send waitlist nurture sequence emails (day 1 / 3 / 7)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be sent without sending.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        now = timezone.now()
        sent, skipped = send_due_nurture_emails(now=now, dry_run=dry_run)
        label = "[DRY RUN] " if dry_run else ""
        self.stdout.write(f"{label}Sent: {sent}  Skipped (not due): {skipped}")
