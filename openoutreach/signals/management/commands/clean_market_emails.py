"""
Wipe scraped junk emails (placeholders, telemetry DSNs, our own address) out of
the FloridaOrg market data so cold outreach never sends to a bad address.

    python manage.py clean_market_emails            # clean all 114k orgs
    python manage.py clean_market_emails --dry-run  # report only
"""
from django.core.management.base import BaseCommand

from openoutreach.signals.email_hygiene import clean_junk_emails, is_junk_email
from openoutreach.signals.models import FloridaOrg


class Command(BaseCommand):
    help = "Blank out junk/placeholder/telemetry emails scraped into FloridaOrg.contact_email."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        if options["dry_run"]:
            n = sum(1 for o in FloridaOrg.objects.exclude(contact_email="")
                    .iterator(chunk_size=5000) if is_junk_email(o.contact_email))
            self.stdout.write(f"[dry-run] {n:,} junk emails would be cleared.")
            return
        cleaned = clean_junk_emails(FloridaOrg.objects.all())
        self.stdout.write(self.style.SUCCESS(f"Cleared {cleaned:,} junk emails."))
