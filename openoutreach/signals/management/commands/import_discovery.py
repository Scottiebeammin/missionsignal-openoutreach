"""Import discovered funders / partners / resources from a JSON file.

The JSON is produced by the discovery agent (Hermes web research). Each item is
created as global reference data (active=True) so the matching engine scores it
for any project's Opportunity Web. AI-discovered records are flagged
verification_status="needs_review" so a human verifies the source before it is
shown to a client as trusted.

Usage:
    python manage.py import_discovery --file discovery.json
    python manage.py import_discovery --file discovery.json --dry-run

Expected JSON shape:
    {
      "funders":   [{"name","type","geography","focus_areas":[...],"website","why_fit","eligibility_notes","deadline"}],
      "partners":  [{"name","type","geography","focus_areas":[...],"website","why_fit","collaboration_opportunities"}],
      "resources": [{"name","type","geography","focus_areas":[...],"resource_categories":[...],"website","why_fit","eligibility_notes"}]
    }
"""

import json

from django.core.management.base import BaseCommand, CommandError

from openoutreach.funding.models import Funder, PartnerOrganization, ResourceProvider


def _enum_or_other(model, field_name, value):
    """Map a free-text type to a valid choice, falling back to 'other'."""
    valid = {c[0] for c in model._meta.get_field(field_name).choices or []}
    v = (value or "").strip().lower().replace(" ", "_").replace("-", "_")
    return v if v in valid else "other"


def _extract_json(raw: str) -> dict:
    """Tolerate markdown fences / prose around the JSON object."""
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        raise CommandError("No JSON object found in the file.")
    return json.loads(raw[start : end + 1])


DISCOVERY_NOTE = "Discovered via automated web research; pending human verification."


class Command(BaseCommand):
    help = "Import discovered funders/partners/resources (JSON) as reference data."

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help="Path to the discovery JSON file.")
        parser.add_argument("--dry-run", action="store_true", help="Parse and report, write nothing.")

    def handle(self, *args, **opts):
        with open(opts["file"], encoding="utf-8") as fh:
            data = _extract_json(fh.read())

        dry = opts["dry_run"]
        counts = {"funders": [0, 0], "partners": [0, 0], "resources": [0, 0]}  # [created, updated]

        for item in data.get("funders", []):
            fields = {
                "funder_type": _enum_or_other(Funder, "funder_type", item.get("type")),
                "geography": item.get("geography", ""),
                "focus_areas": item.get("focus_areas", []),
                "eligibility_notes": item.get("eligibility_notes", ""),
                "website": item.get("website", ""),
                "notes": item.get("why_fit", ""),
                "source_urls": [item["website"]] if item.get("website") else [],
                "source_notes": DISCOVERY_NOTE + (f" Deadline: {item['deadline']}." if item.get("deadline") else ""),
                "verification_status": Funder.VerificationStatus.NEEDS_REVIEW,
                "active": True,
            }
            self._upsert(Funder, item["name"], fields, counts["funders"], dry)

        for item in data.get("partners", []):
            fields = {
                "partner_type": _enum_or_other(PartnerOrganization, "partner_type", item.get("type")),
                "geography": item.get("geography", ""),
                "focus_areas": item.get("focus_areas", []),
                "collaboration_opportunities": item.get("collaboration_opportunities", "") or item.get("why_fit", ""),
                "website": item.get("website", ""),
                "mission_alignment_notes": item.get("why_fit", ""),
                "source_urls": [item["website"]] if item.get("website") else [],
                "source_notes": DISCOVERY_NOTE,
                "verification_status": PartnerOrganization.VerificationStatus.NEEDS_REVIEW,
                "active": True,
            }
            self._upsert(PartnerOrganization, item["name"], fields, counts["partners"], dry)

        for item in data.get("resources", []):
            fields = {
                "resource_type": _enum_or_other(ResourceProvider, "resource_type", item.get("type")),
                "geography": item.get("geography", ""),
                "focus_areas": item.get("focus_areas", []),
                "resource_categories": item.get("resource_categories", []),
                "eligibility_notes": item.get("eligibility_notes", ""),
                "website": item.get("website", ""),
                "notes": item.get("why_fit", ""),
                "active": True,
            }
            self._upsert(ResourceProvider, item["name"], fields, counts["resources"], dry)

        prefix = "[dry-run] would " if dry else ""
        for kind, (c, u) in counts.items():
            self.stdout.write(self.style.SUCCESS(f"{prefix}{kind}: {c} created, {u} updated"))

    def _upsert(self, model, name, fields, counter, dry):
        name = (name or "").strip()
        if not name:
            return
        if dry:
            exists = model.objects.filter(name=name).exists()
            counter[1 if exists else 0] += 1
            return
        _, created = model.objects.update_or_create(name=name, defaults=fields)
        counter[0 if created else 1] += 1
