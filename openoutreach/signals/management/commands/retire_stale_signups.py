"""
management command: retire_stale_signups

Takes waitlist signups out of the nurture sequence without mailing them, by
marking the sequence complete (nurture_step = MAX_STEP).

Why this exists: the nurture cron ran daily for a month with no EMAIL_* vars, so
nothing sent and nothing advanced. The queue that accumulated behind it is not a
backlog to work through — it is history. Mailing it would fire thousands of
messages at addresses that signed up weeks or months ago, most of them bot-
generated, from a domain being reputation-warmed at a handful of sends a day.

Retiring is deliberately not deleting: the rows stay for the record, they simply
stop being candidates. No SalesLead is created — a retired signup was excluded
from the sequence, it did not complete it.

Reports and changes nothing unless --confirm is passed.

Usage:
    python manage.py retire_stale_signups                        # report only
    python manage.py retire_stale_signups --before 2026-08-30
    python manage.py retire_stale_signups --before 2026-08-30 --confirm
"""
from datetime import datetime, time

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count
from django.utils import timezone

from openoutreach.signals.models import InterestSignup
from openoutreach.signals.nurture import MAX_STEP


class Command(BaseCommand):
    help = "Retire waitlist signups from the nurture sequence without mailing them."

    def add_arguments(self, parser):
        parser.add_argument(
            "--before",
            help="Retire signups created before this date (YYYY-MM-DD). "
                 "Defaults to now, i.e. everything currently queued.",
        )
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Actually write. Without it the command only reports.",
        )

    def handle(self, *args, **options):
        cutoff = timezone.now()
        if options["before"]:
            try:
                parsed = datetime.strptime(options["before"], "%Y-%m-%d")
            except ValueError:
                raise CommandError("--before must be YYYY-MM-DD")
            cutoff = timezone.make_aware(datetime.combine(parsed.date(), time.min))

        queryset = InterestSignup.objects.filter(
            nurture_step__lt=MAX_STEP,
            status__in=[InterestSignup.Status.NEW, InterestSignup.Status.REVIEWED],
            created_at__lt=cutoff,
        )
        total = queryset.count()

        self.stdout.write(f"Cutoff: signups created before {cutoff.isoformat()}")
        self.stdout.write(f"In the nurture sequence and older than the cutoff: {total}")
        if total:
            distinct = queryset.values("email").distinct().count()
            self.stdout.write(f"  distinct email addresses: {distinct}")
            by_step = queryset.values("nurture_step").annotate(n=Count("pk")).order_by("nurture_step")
            for row in by_step:
                self.stdout.write(f"  at nurture_step={row['nurture_step']}: {row['n']}")

        if not options["confirm"]:
            self.stdout.write(self.style.WARNING(
                "\nReport only — nothing written. Re-run with --confirm to retire these."
            ))
            return

        updated = queryset.update(nurture_step=MAX_STEP)
        self.stdout.write(self.style.SUCCESS(
            f"\nRetired {updated} signup(s). They will never receive the sequence. "
            "No SalesLead rows were created."
        ))
