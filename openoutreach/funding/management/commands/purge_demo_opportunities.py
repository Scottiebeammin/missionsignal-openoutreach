"""
Purge demo/seed opportunities — rows whose source is a placeholder URL
(…example.org / …example.com) or a "Demo" source reference. These are seed data,
never real grants; they now show clients "Verify first" and add only noise. Real
federal (Grants.gov) opportunities with genuine source links are left untouched.

    python manage.py purge_demo_opportunities --dry-run   # preview, delete nothing
    python manage.py purge_demo_opportunities             # delete them

Idempotent and safe to re-run — a clean database deletes 0.
"""
from django.core.management.base import BaseCommand

from openoutreach.funding.models import Opportunity


def _is_demo(o) -> bool:
    urls = " ".join(o.source_urls or []).lower()
    refs = str(o.source_references or "").lower()
    return ".example." in urls or "demo" in refs or "demo" in (o.source_name or "").lower()


class Command(BaseCommand):
    help = "Delete demo/seed opportunities (placeholder .example. URLs or 'Demo' source refs)."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Preview what would be deleted.")

    def handle(self, *args, **options):
        ids = [o.pk for o in Opportunity.objects.all() if _is_demo(o)]
        total = Opportunity.objects.count()

        if options["dry_run"]:
            self.stdout.write(f"[dry-run] {len(ids)} of {total} opportunities are demo/seed and would be deleted:")
            for o in Opportunity.objects.filter(pk__in=ids)[:25]:
                src = (o.source_urls or ["—"])[0]
                proj = o.project.organization.name if o.project and o.project.organization else "global"
                self.stdout.write(f"   - {o.name[:46]:46} [{proj[:20]}] {src[:38]}")
            if len(ids) > 25:
                self.stdout.write(f"   … and {len(ids) - 25} more")
            return

        deleted, _ = Opportunity.objects.filter(pk__in=ids).delete()
        remaining = Opportunity.objects.count()
        confirmed = sum(1 for o in Opportunity.objects.all() if o.is_confirmed)
        self.stdout.write(self.style.SUCCESS(
            f"Deleted {len(ids)} demo/seed opportunities ({deleted} rows incl. related). "
            f"Remaining: {remaining} ({confirmed} Confirmed, {remaining - confirmed} Verify-first)."
        ))
