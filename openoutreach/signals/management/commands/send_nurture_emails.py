"""
management command: send_nurture_emails

Sends the waitlist nurture sequence (day 1 / day 3 / day 7) to signups that
haven't yet received each email. Safe to run repeatedly — uses nurture_step to
track position and created_at as the timing anchor.

Exits non-zero when every attempted send failed, so a broken transport surfaces
as a failed cron run instead of a green one. See NurtureRun.total_failure.

Usage:
    python manage.py send_nurture_emails           # live send
    python manage.py send_nurture_emails --dry-run # preview only
"""
from django.core.management.base import BaseCommand, CommandError
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
        run = send_due_nurture_emails(now=timezone.now(), dry_run=dry_run)
        label = "[DRY RUN] " if dry_run else ""
        self.stdout.write(
            f"{label}Sent: {run.sent}  Failed: {run.failed}  "
            f"Suppressed (opted out / aged out): {run.suppressed}  "
            f"Capped (over daily limit): {run.capped}  "
            f"Skipped (not due): {run.skipped}"
        )

        if run.total_failure:
            raise CommandError(
                f"Every nurture send failed ({run.failed} attempted, 0 delivered). "
                "This is a transport failure, not a data problem — check the EMAIL_* "
                "environment variables on this service."
            )

        if run.failed:
            self.stdout.write(self.style.WARNING(
                f"{run.failed} send(s) failed but {run.sent} succeeded — see the log."
            ))
