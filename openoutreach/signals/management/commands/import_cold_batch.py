"""
Load the curated Ocala + Gainesville cold batch into the pipeline from a
committed data file — self-contained, so it works on any environment WITHOUT the
114k-org FloridaOrg market table loaded (unlike seed_cold_batch, which builds the
same batch from that table for local curation).

Reads data/cold-batch.json (20 emailable → the Outreach Cockpit Cold tab, 6
phone-only "keepers" → the Call List with their call scripts). Idempotent:
matches emailable leads by email and call-list leads by organization, updating in
place. Never overwrites a lead already marked sent. Postgres-safe, no LLM.

    python manage.py import_cold_batch
    python manage.py import_cold_batch --dry-run
"""
import json

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from openoutreach.signals.models import SalesLead

DATA = "data/cold-batch.json"

# Fields carried from the snapshot onto each lead (email/organization are the
# match keys and set on create only).
_FIELDS = ("name", "role", "phone", "focus_area", "why_fit", "subject_line", "outreach_draft", "source")


class Command(BaseCommand):
    help = "Load the curated cold batch (20 emailable + 6 call-list) from data/cold-batch.json — self-contained."

    def add_arguments(self, parser):
        parser.add_argument("--data", default=DATA)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        try:
            batch = json.loads(open(options["data"]).read())
        except OSError as exc:
            raise CommandError(f"Cannot read {options['data']}: {exc}")

        dry = options["dry_run"]
        created = updated = skipped_sent = 0

        def apply(rec, existing):
            nonlocal created, updated, skipped_sent
            lead = existing
            if lead and lead.email_status == "sent":
                skipped_sent += 1
                return
            if lead is None:
                if not dry:
                    lead = SalesLead.objects.create(
                        organization=rec.get("organization", ""),
                        email=rec.get("email", ""),
                        list_segment=rec["list_segment"],
                        email_status="not_sent",
                        **{f: rec.get(f, "") for f in _FIELDS},
                    )
                created += 1
            else:
                if not dry:
                    for f in _FIELDS:
                        setattr(lead, f, rec.get(f, ""))
                    lead.updated_at = timezone.now()
                    lead.save(update_fields=list(_FIELDS) + ["updated_at"])
                updated += 1

        for rec in batch.get("emailable", []):
            existing = (SalesLead.objects
                        .filter(list_segment=SalesLead.Segment.COLD_FLORIDA_CRM, email__iexact=rec["email"])
                        .first())
            apply(rec, existing)

        for rec in batch.get("call_list", []):
            existing = (SalesLead.objects
                        .filter(list_segment=SalesLead.Segment.COLD_CALL_LIST,
                                organization__iexact=rec["organization"])
                        .first())
            apply(rec, existing)

        tag = "[dry-run] " if dry else ""
        self.stdout.write(self.style.SUCCESS(
            f"{tag}Cold batch: {created} created, {updated} updated, {skipped_sent} skipped (already sent). "
            f"Emailable → Cockpit Cold tab; call-list → Call List."
        ))
