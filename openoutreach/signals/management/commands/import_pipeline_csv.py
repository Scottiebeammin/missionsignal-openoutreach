"""
Import the canonical n8n pipeline CSV into the SalesLead command center.

Usage:
    python manage.py import_pipeline_csv /path/to/pipeline.csv [--dry-run]

Canonical columns (case-insensitive; extra columns are appended to notes):
    lead_id, dedup_key, is_warm, list_segment, warmth, campaign_track, ref,
    organization, contact_name, first_name, last_name, role_title, email,
    relationship_depth, focus_angle, subject_line, stage, next_action,
    why_fit, website, email_status, source, date_added, last_updated, notes,
    region

Reconcile rules:
    - Upsert on normalized (lowercased/stripped) email; fall back to
      (contact_name, organization) when email is blank.
    - Warm wins: an existing warm lead is never flipped to cold
      (source/list_segment stay warm even if the incoming row says cold).
    - Never downgrade a worked lead's status (only NEW leads take the
      incoming stage).
    - Non-empty incoming fields refresh existing values; blanks never
      clobber hand-entered data.
"""

import csv

from django.core.management.base import BaseCommand, CommandError

from openoutreach.signals.models import SalesLead

# Canonical "stage" values → pipeline status (same style as import_warm_contacts).
_STAGE_MAP = {
    "not started": SalesLead.Status.NEW,
    "new": SalesLead.Status.NEW,
    "reached out": SalesLead.Status.REACHED_OUT,
    "reached_out": SalesLead.Status.REACHED_OUT,
    "call scheduled": SalesLead.Status.CALL_SCHEDULED,
    "call_scheduled": SalesLead.Status.CALL_SCHEDULED,
    "call done": SalesLead.Status.CALL_DONE,
    "call_done": SalesLead.Status.CALL_DONE,
    "closed": SalesLead.Status.CLOSED,
    "nurturing": SalesLead.Status.NURTURING,
    "passed": SalesLead.Status.PASSED,
}

# Canonical headers we map explicitly; everything else goes to notes.
_KNOWN = {
    "lead_id", "dedup_key", "is_warm", "list_segment", "warmth",
    "campaign_track", "ref", "organization", "contact_name", "first_name",
    "last_name", "role_title", "email", "relationship_depth", "focus_angle",
    "subject_line", "stage", "next_action", "why_fit", "website",
    "email_status", "source", "date_added", "last_updated", "notes", "region",
}

_TRUTHY = {"true", "1", "yes", "y", "t"}


def _norm_row(row: dict) -> dict:
    """Lowercase headers, strip whitespace on keys and values."""
    return {
        (k or "").strip().lower(): (v or "").strip()
        for k, v in row.items()
        if k is not None
    }


def _build_why_fit(row: dict) -> str:
    parts = []
    if row.get("why_fit"):
        parts.append(row["why_fit"])
    if row.get("relationship_depth"):
        parts.append(f"Relationship: {row['relationship_depth']}")
    return "\n".join(parts)


def _build_notes(row: dict) -> str:
    parts = []
    if row.get("focus_angle"):
        parts.append(f"Focus angle: {row['focus_angle']}")
    if row.get("next_action"):
        parts.append(f"Next action: {row['next_action']}")
    if row.get("campaign_track"):
        parts.append(f"Campaign track: {row['campaign_track']}")
    if row.get("website"):
        parts.append(f"Website: {row['website']}")
    if row.get("ref"):
        parts.append(f"Ref: {row['ref']}")
    if row.get("notes"):
        parts.append(row["notes"])
    # Unknown columns preserved verbatim so no data is lost.
    for key in sorted(set(row) - _KNOWN):
        if row[key]:
            parts.append(f"{key}: {row[key]}")
    return "\n".join(parts)


class Command(BaseCommand):
    help = "Import the canonical n8n pipeline CSV into SalesLead (idempotent upsert by email; warm wins)."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", help="Path to the canonical pipeline CSV")
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
            for raw in reader:
                row = _norm_row(raw)
                first = row.get("first_name", "")
                last = row.get("last_name", "")
                name = row.get("contact_name") or f"{first} {last}".strip()
                org = row.get("organization", "")
                email = (row.get("email") or row.get("dedup_key") or "").lower()
                if not name and not org:
                    skipped += 1
                    continue

                is_warm = row.get("is_warm", "").lower() in _TRUTHY
                warmth = row.get("warmth", "").lower()
                if warmth not in SalesLead.Warmth.values:
                    warmth = ""
                stage = _STAGE_MAP.get(row.get("stage", "").lower(), SalesLead.Status.NEW)

                if is_warm:
                    source = SalesLead.Source.WARM
                    segment = SalesLead.Segment.WARM
                else:
                    source = SalesLead.Source.COLD
                    segment = SalesLead.Segment.COLD_FLORIDA_CRM
                # Respect an explicit canonical list_segment when valid.
                seg_in = row.get("list_segment", "").lower()
                if seg_in in SalesLead.Segment.values:
                    segment = seg_in
                    if segment == SalesLead.Segment.WARM:
                        source = SalesLead.Source.WARM

                fields = {
                    "name": name or org,
                    "organization": org,
                    "email": email,
                    "role": row.get("role_title", "")[:200],
                    "warmth": warmth,
                    "region": row.get("region", "")[:120],
                    "focus_area": row.get("focus_angle", "")[:200],
                    "why_fit": _build_why_fit(row),
                    "subject_line": row.get("subject_line", "")[:300],
                    "email_status": row.get("email_status", "")[:30],
                    "notes": _build_notes(row),
                }

                if email:
                    existing = SalesLead.objects.filter(email__iexact=email).first()
                else:
                    existing = SalesLead.objects.filter(
                        name__iexact=name, organization__iexact=org
                    ).first()

                if existing:
                    if not dry_run:
                        for field, value in fields.items():
                            # Refresh only non-empty incoming fields.
                            if value:
                                setattr(existing, field, value)
                        # Warm wins: never flip an existing warm lead to cold.
                        existing_warm = (
                            existing.source == SalesLead.Source.WARM
                            or existing.list_segment == SalesLead.Segment.WARM
                        )
                        if existing_warm or is_warm or segment == SalesLead.Segment.WARM:
                            existing.source = SalesLead.Source.WARM
                            existing.list_segment = SalesLead.Segment.WARM
                        else:
                            existing.list_segment = segment
                            # Don't clobber referral/inbound provenance with "cold".
                            if existing.source in (SalesLead.Source.WARM, SalesLead.Source.COLD):
                                existing.source = source
                        # Never downgrade a worked lead back to NEW.
                        if existing.status == SalesLead.Status.NEW:
                            existing.status = stage
                        existing.save()  # auto_now bumps updated_at (last_updated)
                    updated += 1
                else:
                    if not dry_run:
                        SalesLead.objects.create(
                            status=stage, source=source, list_segment=segment, **fields
                        )
                    created += 1

        mode = "DRY RUN — " if dry_run else ""
        self.stdout.write(self.style.SUCCESS(
            f"{mode}pipeline import: {created} created, {updated} updated, {skipped} skipped"
        ))
