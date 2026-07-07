"""
Load Marcus's warm network into the pipeline from a committed data file —
self-contained, so production gets all the warm leads (with the hand-written
drafts, restored addressee names, and CCs already baked in) WITHOUT needing the
original warm-list CSV. Companion to import_cold_batch.

Idempotent: matches by email, updates content in place, NEVER overwrites a lead
already marked sent, and NEVER downgrades an existing lead's pipeline status
(only content/draft fields refresh on update). Postgres-safe, no LLM.

    python manage.py import_warm_batch
    python manage.py import_warm_batch --dry-run
"""
import json

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from openoutreach.signals.models import SalesLead

DATA = "data/warm-batch.json"

# Content fields refreshed on every run. status + email_status are set on CREATE
# only, so we never downgrade a lead already worked/sent on production.
_CONTENT = ("organization", "name", "role", "phone", "warmth", "focus_area",
            "why_fit", "subject_line", "outreach_draft", "cc_emails", "source")


class Command(BaseCommand):
    help = "Load the warm network (leads + hand-written drafts) from data/warm-batch.json — self-contained."

    def add_arguments(self, parser):
        parser.add_argument("--data", default=DATA)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        try:
            rows = json.loads(open(options["data"]).read())
        except OSError as exc:
            raise CommandError(f"Cannot read {options['data']}: {exc}")

        dry = options["dry_run"]
        created = updated = skipped_sent = skipped_noemail = 0
        for rec in rows:
            email = (rec.get("email") or "").strip()
            if not email:
                skipped_noemail += 1
                continue
            lead = SalesLead.objects.filter(
                list_segment=SalesLead.Segment.WARM, email__iexact=email).first()
            if lead and lead.email_status == "sent":
                skipped_sent += 1
                continue
            if lead is None:
                if not dry:
                    SalesLead.objects.create(
                        email=email,
                        list_segment=SalesLead.Segment.WARM,
                        email_status=rec.get("email_status") or "not_sent",
                        status=rec.get("status") or SalesLead.Status.NEW,
                        **{f: rec.get(f, "") for f in _CONTENT},
                    )
                created += 1
            else:
                if not dry:
                    for f in _CONTENT:
                        setattr(lead, f, rec.get(f, ""))
                    lead.updated_at = timezone.now()
                    lead.save(update_fields=list(_CONTENT) + ["updated_at"])
                updated += 1

        tag = "[dry-run] " if dry else ""
        self.stdout.write(self.style.SUCCESS(
            f"{tag}Warm batch: {created} created, {updated} updated, "
            f"{skipped_sent} skipped (already sent), {skipped_noemail} skipped (no email). "
            f"Warm tab now populated."
        ))
