"""
Import the founder's Master Contact list (warm-list CSV) into the SalesLead pipeline.

Usage:
    python manage.py import_warm_contacts /path/to/warm-list-master.csv [--dry-run]

Expected columns (extra columns are ignored):
    rank, org_name, contact_name, role, email, relationship_warmth,
    focus_area, shared_memory, why_a_fit, stage, next_action,
    next_touch_date, website, notes

Idempotent: rows are matched by email (case-insensitive), falling back to
(contact_name, org_name) when the email cell is blank. Existing SalesLeads are
updated in place — status is NEVER downgraded (a lead already worked in the
pipeline keeps its stage; only notes/contact fields refresh).
"""

import csv
from datetime import date, datetime

from django.core.management.base import BaseCommand, CommandError

from openoutreach.signals.models import SalesLead

# CSV "stage" values → pipeline status. Anything unrecognized maps to NEW.
_STAGE_MAP = {
    "not started": SalesLead.Status.NEW,
    "reached out": SalesLead.Status.REACHED_OUT,
    "call scheduled": SalesLead.Status.CALL_SCHEDULED,
    "call done": SalesLead.Status.CALL_DONE,
    "closed": SalesLead.Status.CLOSED,
    "nurturing": SalesLead.Status.NURTURING,
    "passed": SalesLead.Status.PASSED,
}


def _parse_date(value: str) -> date | None:
    value = (value or "").strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _build_notes(row: dict) -> str:
    parts = []
    if row.get("relationship_warmth", "").strip():
        parts.append(f"Warmth: {row['relationship_warmth'].strip()}")
    if row.get("shared_memory", "").strip():
        parts.append(f"Shared memory: {row['shared_memory'].strip()}")
    if row.get("why_a_fit", "").strip():
        parts.append(f"Why a fit: {row['why_a_fit'].strip()}")
    if row.get("focus_area", "").strip():
        parts.append(f"Focus area: {row['focus_area'].strip()}")
    if row.get("next_action", "").strip():
        parts.append(f"Next action: {row['next_action'].strip()}")
    if row.get("website", "").strip():
        parts.append(f"Website: {row['website'].strip()}")
    if row.get("notes", "").strip():
        parts.append(row["notes"].strip())
    return "\n".join(parts)


class Command(BaseCommand):
    help = "Import the warm Master Contact list CSV into the SalesLead pipeline (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", help="Path to warm-list-master.csv")
        parser.add_argument("--dry-run", action="store_true", help="Report without writing")

    def handle(self, *args, **options):
        path = options["csv_path"]
        dry_run = options["dry_run"]
        try:
            fh = open(path, newline="", encoding="utf-8-sig")
        except OSError as exc:
            raise CommandError(f"Cannot open {path}: {exc}")

        created = updated = skipped = 0
        with fh:
            reader = csv.DictReader(fh)
            for row in reader:
                name = (row.get("contact_name") or "").strip()
                org = (row.get("org_name") or "").strip()
                email = (row.get("email") or "").strip().lower()
                if not name and not org:
                    skipped += 1
                    continue

                if email:
                    existing = SalesLead.objects.filter(email__iexact=email).first()
                else:
                    existing = SalesLead.objects.filter(
                        name__iexact=name, organization__iexact=org
                    ).first()

                stage = _STAGE_MAP.get((row.get("stage") or "").strip().lower(), SalesLead.Status.NEW)
                raw_warmth = (row.get("relationship_warmth") or "").strip().lower()
                warmth = raw_warmth if raw_warmth in {"hot", "warm", "reconnect", "cold"} else ""
                why_bits = [b.strip() for b in (row.get("why_a_fit", ""), row.get("shared_memory", "")) if b and b.strip()]
                fields = {
                    "name": name or org,
                    "organization": org,
                    "email": email,
                    "role": (row.get("role") or "").strip()[:200],
                    "source": SalesLead.Source.WARM,
                    "list_segment": SalesLead.Segment.WARM,
                    "warmth": warmth,
                    "focus_area": (row.get("focus_area") or "").strip()[:200],
                    "why_fit": " — ".join(why_bits),
                    "notes": _build_notes(row),
                    "next_follow_up": _parse_date(row.get("next_touch_date", "")),
                }

                if existing:
                    if not dry_run:
                        for field, value in fields.items():
                            # Don't blank out data the founder added by hand.
                            if value:
                                setattr(existing, field, value)
                        # Never downgrade a worked lead back to NEW.
                        if existing.status == SalesLead.Status.NEW:
                            existing.status = stage
                        existing.save()
                    updated += 1
                else:
                    if not dry_run:
                        SalesLead.objects.create(status=stage, **fields)
                    created += 1

        mode = "DRY RUN — " if dry_run else ""
        self.stdout.write(self.style.SUCCESS(
            f"{mode}warm contacts import: {created} created, {updated} updated, {skipped} skipped"
        ))
