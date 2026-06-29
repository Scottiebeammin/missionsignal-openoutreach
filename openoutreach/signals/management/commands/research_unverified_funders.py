"""
Management command: research_unverified_funders

Runs AI research on all unverified funders to fill in focus areas, geography,
grant ranges, and deadlines. Sets verification_status to needs_review after
research so the operator knows to check them.

Usage:
  python manage.py research_unverified_funders
  python manage.py research_unverified_funders --limit 10
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run AI research on unverified funders and flag them for operator review."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=0, help="Max funders to process (0 = all)")

    def handle(self, *args, **options):
        from openoutreach.funding.models import Funder
        from openoutreach.signals.research import research_funder
        from django.utils import timezone

        qs = Funder.objects.filter(verification_status=Funder.VerificationStatus.UNVERIFIED, active=True).order_by("name")
        if options["limit"]:
            qs = qs[: options["limit"]]

        funders = list(qs)
        if not funders:
            self.stdout.write("No unverified funders found.")
            return

        self.stdout.write(f"Researching {len(funders)} unverified funder(s)...")
        success = 0
        for funder in funders:
            self.stdout.write(f"  → {funder.name}... ", ending="")
            try:
                research_funder(funder)
                # Bump to needs_review so operator knows it's been looked at
                funder.verification_status = Funder.VerificationStatus.NEEDS_REVIEW
                funder.last_reviewed_at = timezone.now()
                funder.save(update_fields=["verification_status", "last_reviewed_at"])
                self.stdout.write(self.style.SUCCESS("done → needs_review"))
                success += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"FAILED: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Complete. {success}/{len(funders)} researched."))
        self.stdout.write("Visit /operator/funders/?status=needs_review to review.")
