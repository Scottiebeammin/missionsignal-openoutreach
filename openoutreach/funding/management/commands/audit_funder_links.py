"""
Management command: audit_funder_links

Deterministic (no-LLM, no-cost) hallucination check for the Funder database.
For every active funder it inspects the website + source_urls and sorts each
funder into one of four buckets:

  FAKE     – uses an RFC-2606 reserved placeholder domain (example.com/.test/
             .invalid/.localhost). These are invented funders — pure
             hallucination. Safe to archive.
  DEAD     – has URL(s) but none resolve over HTTP (DNS failure / 4xx / 5xx).
  NO_LINK  – no website and no source_urls at all (unverifiable).
  OK       – at least one real URL that responds.

Usage:
  python manage.py audit_funder_links               # report only (no writes)
  python manage.py audit_funder_links --archive-fake # set active=False on FAKE
  python manage.py audit_funder_links --flag         # FAKE/DEAD/NO_LINK -> needs_review
  python manage.py audit_funder_links --status unverified  # limit to one status
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

# Canonical link-check logic lives in the grounding gate — reuse it here.
from openoutreach.funding.grounding import is_reserved_domain as _is_reserved
from openoutreach.funding.grounding import is_reachable as _is_reachable


class Command(BaseCommand):
    help = "Audit funder websites/source URLs for hallucinations and dead links."

    def add_arguments(self, parser):
        parser.add_argument("--status", default="", help="Limit to one verification_status")
        parser.add_argument("--archive-fake", action="store_true",
                            help="Set active=False on funders using reserved/fake domains")
        parser.add_argument("--flag", action="store_true",
                            help="Set FAKE/DEAD/NO_LINK funders to needs_review")

    def handle(self, *args, **options):
        from openoutreach.funding.models import Funder

        qs = Funder.objects.filter(active=True).order_by("name")
        if options["status"]:
            qs = qs.filter(verification_status=options["status"])

        funders = list(qs)
        self.stdout.write(f"Auditing {len(funders)} active funder(s)...\n")

        buckets = {"FAKE": [], "DEAD": [], "NO_LINK": [], "OK": []}

        for f in funders:
            urls = [u for u in ([f.website] + list(f.source_urls or [])) if u]
            if not urls:
                buckets["NO_LINK"].append((f, "no website or source URLs"))
                continue
            if any(_is_reserved(u) for u in urls):
                buckets["FAKE"].append((f, next(u for u in urls if _is_reserved(u))))
                continue
            if any(_is_reachable(u) for u in urls):
                buckets["OK"].append((f, ""))
            else:
                buckets["DEAD"].append((f, urls[0]))

        icon = {"FAKE": "🟥", "DEAD": "🟧", "NO_LINK": "🟨", "OK": "🟩"}
        for bucket in ("FAKE", "DEAD", "NO_LINK", "OK"):
            rows = buckets[bucket]
            self.stdout.write(f"\n{icon[bucket]} {bucket} ({len(rows)})")
            for f, detail in rows:
                line = f"   [{f.verification_status}] {f.name}"
                if detail:
                    line += f"  →  {detail}"
                self.stdout.write(line)

        # ── Optional writes ──
        if options["archive_fake"] and buckets["FAKE"]:
            ids = [f.pk for f, _ in buckets["FAKE"]]
            Funder.objects.filter(pk__in=ids).update(active=False, updated_at=timezone.now())
            self.stdout.write(self.style.SUCCESS(
                f"\nArchived {len(ids)} FAKE funder(s) (active=False) — removed from matching."))

        if options["flag"]:
            to_flag = [f.pk for b in ("FAKE", "DEAD", "NO_LINK") for f, _ in buckets[b]]
            if to_flag:
                Funder.objects.filter(pk__in=to_flag).update(
                    verification_status=Funder.VerificationStatus.NEEDS_REVIEW,
                    last_reviewed_at=timezone.now(),
                )
                self.stdout.write(self.style.SUCCESS(
                    f"Flagged {len(to_flag)} funder(s) → needs_review."))

        if not options["archive_fake"] and not options["flag"]:
            self.stdout.write(self.style.WARNING(
                "\nReport only — no changes written. "
                "Re-run with --archive-fake to deactivate the FAKE funders."))
