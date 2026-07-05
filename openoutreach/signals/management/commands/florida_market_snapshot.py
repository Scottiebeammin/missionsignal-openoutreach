"""
Move the enriched Florida market database between environments.

    python manage.py florida_market_snapshot export            # -> data/florida-market-snapshot.csv.gz (+ counties csv)
    python manage.py florida_market_snapshot import            # <- same files (idempotent upsert by record_id)

Export on the laptop (where the 114k enriched rows live), commit the snapshot
files, deploy, then import once in the Render shell. The snapshot carries EVERY
FloridaOrg field including enrichment (website/phone/email/officer/source),
priority, and service_area — unlike the raw staging CSV, nothing is lost.
"""

import csv
import gzip

from django.core.management.base import BaseCommand, CommandError

from openoutreach.signals.models import CountyRollout, FloridaOrg

SNAPSHOT = "data/florida-market-snapshot.csv.gz"
COUNTIES = "data/florida-county-rollout-snapshot.csv"

ORG_FIELDS = [
    "record_id", "ein", "name", "sort_name", "street", "city", "county", "region",
    "state", "zip_code", "subsection", "ntee_code", "ntee_sector", "ruling_month",
    "asset_amount", "income_amount", "priority", "relationship_stage", "next_action",
    "service_area", "website", "phone", "contact_email", "principal_officer",
    "contact_source",
]
COUNTY_FIELDS = [
    "county", "rollout_tier", "region", "owner", "status",
    "nonprofit_count", "high_priority_count", "funder_starter_count", "notes",
]


class Command(BaseCommand):
    help = "Export/import the full enriched FloridaOrg + CountyRollout dataset as a portable snapshot."

    def add_arguments(self, parser):
        parser.add_argument("action", choices=["export", "import"])
        parser.add_argument("--snapshot", default=SNAPSHOT)
        parser.add_argument("--counties", default=COUNTIES)

    def handle(self, *args, **options):
        if options["action"] == "export":
            self._export(options)
        else:
            self._import(options)

    def _export(self, options):
        n = 0
        with gzip.open(options["snapshot"], "wt", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(ORG_FIELDS)
            for org in FloridaOrg.objects.all().iterator(chunk_size=5000):
                writer.writerow([getattr(org, f) if getattr(org, f) is not None else "" for f in ORG_FIELDS])
                n += 1
        with open(options["counties"], "w", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(COUNTY_FIELDS)
            for c in CountyRollout.objects.all():
                writer.writerow([getattr(c, f) if getattr(c, f) is not None else "" for f in COUNTY_FIELDS])
        self.stdout.write(self.style.SUCCESS(
            f"Exported {n:,} orgs -> {options['snapshot']} and {CountyRollout.objects.count()} counties -> {options['counties']}"
        ))

    def _import(self, options):
        try:
            fh = gzip.open(options["snapshot"], "rt", newline="")
        except OSError as exc:
            raise CommandError(f"Cannot open snapshot: {exc}")
        created = updated = unchanged = 0
        with fh:
            reader = csv.DictReader(fh)
            existing = {o.record_id: o for o in FloridaOrg.objects.all().iterator(chunk_size=5000)}
            to_create, to_update = [], []
            int_fields = {"asset_amount", "income_amount"}
            for row in reader:
                vals = {}
                for f in ORG_FIELDS:
                    v = row.get(f, "")
                    if f in int_fields:
                        vals[f] = int(v) if v not in ("", "None") else None
                    else:
                        vals[f] = v or ""
                rid = vals["record_id"]
                cur = existing.get(rid)
                if cur is None:
                    to_create.append(FloridaOrg(**vals))
                    created += 1
                else:
                    changed = False
                    for f, v in vals.items():
                        if getattr(cur, f) != v and f != "record_id":
                            setattr(cur, f, v)
                            changed = True
                    if changed:
                        to_update.append(cur)
                        updated += 1
                    else:
                        unchanged += 1
                if len(to_create) >= 2000:
                    FloridaOrg.objects.bulk_create(to_create)
                    to_create = []
                if len(to_update) >= 2000:
                    FloridaOrg.objects.bulk_update(to_update, [f for f in ORG_FIELDS if f != "record_id"])
                    to_update = []
            if to_create:
                FloridaOrg.objects.bulk_create(to_create)
            if to_update:
                FloridaOrg.objects.bulk_update(to_update, [f for f in ORG_FIELDS if f != "record_id"])
        # counties (small)
        cn = 0
        try:
            with open(options["counties"], newline="") as cfh:
                for row in csv.DictReader(cfh):
                    CountyRollout.objects.update_or_create(
                        county=row["county"],
                        defaults={f: (int(row[f]) if f.endswith("_count") and row[f] else row[f] or "")
                                  if f != "county" else row[f]
                                  for f in COUNTY_FIELDS if f != "county"},
                    )
                    cn += 1
        except OSError:
            self.stdout.write("(no counties file — skipped)")
        self.stdout.write(self.style.SUCCESS(
            f"Import done: {created:,} created, {updated:,} updated, {unchanged:,} unchanged orgs; {cn} counties upserted."
        ))
