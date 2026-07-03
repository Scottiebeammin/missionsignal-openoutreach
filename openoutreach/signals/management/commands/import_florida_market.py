"""Import the Florida Market Database staging CSVs (stdlib csv only).

Usage:
    .venv/bin/python manage.py import_florida_market \
        [--master data/florida-crm-staging/master_crm.csv] \
        [--counties data/florida-crm-staging/county_rollout.csv]

Idempotent: FloridaOrg upserts by record_id (bulk_create for new rows,
bulk_update for changed rows, skip if unchanged); CountyRollout upserts by
county. Never touches promoted_lead on existing rows.
"""

import csv

from django.core.management.base import BaseCommand, CommandError

from openoutreach.signals.models import CountyRollout, FloridaOrg

BATCH = 2000

ORG_FIELDS = [
    "ein", "name", "sort_name", "street", "city", "county", "region",
    "state", "zip_code", "subsection", "ntee_code", "ntee_sector",
    "ruling_month", "asset_amount", "income_amount",
]


def _to_int(value):
    value = (value or "").strip().replace(",", "")
    if not value:
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def _org_values(row):
    g = lambda key: (row.get(key) or "").strip()  # noqa: E731
    return {
        "ein": g("EIN"),
        "name": g("Organization"),
        "sort_name": g("Sort Name"),
        "street": g("Street"),
        "city": g("City"),
        "county": g("County"),
        "region": g("Region"),
        "state": g("State"),
        "zip_code": g("ZIP"),
        "subsection": g("Subsection"),
        "ntee_code": g("NTEE Code"),
        "ntee_sector": g("NTEE Sector"),
        "ruling_month": g("Ruling Month"),
        "asset_amount": _to_int(row.get("Asset Amount")),
        "income_amount": _to_int(row.get("Income Amount")),
    }


class Command(BaseCommand):
    help = "Import Florida market universe + county rollout staging CSVs."

    def add_arguments(self, parser):
        parser.add_argument("--master", default="data/florida-crm-staging/master_crm.csv")
        parser.add_argument("--counties", default="data/florida-crm-staging/county_rollout.csv")

    def handle(self, *args, **options):
        created, updated, unchanged = self._import_orgs(options["master"])
        counties = self._import_counties(options["counties"])
        self.stdout.write(self.style.SUCCESS(
            f"Done. FloridaOrg: {created} created, {updated} updated, "
            f"{unchanged} unchanged (total {FloridaOrg.objects.count()}). "
            f"CountyRollout: {counties} upserted (total {CountyRollout.objects.count()})."
        ))

    # ── FloridaOrg ────────────────────────────────────────────────────────

    def _import_orgs(self, path):
        existing = {o.record_id: o for o in FloridaOrg.objects.all()}
        created = updated = unchanged = processed = 0
        to_create, to_update = [], []

        def flush():
            nonlocal to_create, to_update
            if to_create:
                FloridaOrg.objects.bulk_create(to_create, batch_size=BATCH)
                to_create = []
            if to_update:
                FloridaOrg.objects.bulk_update(to_update, ORG_FIELDS, batch_size=BATCH)
                to_update = []

        try:
            fh = open(path, newline="", encoding="utf-8-sig")
        except OSError as e:
            raise CommandError(f"Cannot open master CSV: {e}")
        with fh:
            for row in csv.DictReader(fh):
                record_id = (row.get("Record ID") or "").strip()
                if not record_id:
                    continue
                values = _org_values(row)
                obj = existing.get(record_id)
                if obj is None:
                    to_create.append(FloridaOrg(record_id=record_id, **values))
                    created += 1
                else:
                    if any(getattr(obj, f) != values[f] for f in ORG_FIELDS):
                        for f in ORG_FIELDS:
                            setattr(obj, f, values[f])
                        to_update.append(obj)
                        updated += 1
                    else:
                        unchanged += 1
                processed += 1
                if len(to_create) >= BATCH or len(to_update) >= BATCH:
                    flush()
                if processed % 20000 == 0:
                    self.stdout.write(f"  ...{processed:,} org rows processed")
        flush()
        return created, updated, unchanged

    # ── CountyRollout ─────────────────────────────────────────────────────

    def _import_counties(self, path):
        count = 0
        try:
            fh = open(path, newline="", encoding="utf-8-sig")
        except OSError as e:
            raise CommandError(f"Cannot open county CSV: {e}")
        with fh:
            for row in csv.DictReader(fh):
                county = (row.get("County") or "").strip()
                if not county:
                    continue
                CountyRollout.objects.update_or_create(
                    county=county,
                    defaults={
                        "rollout_tier": (row.get("Rollout Tier") or "").strip(),
                        "region": (row.get("Region") or "").strip(),
                        "owner": (row.get("Owner") or "").strip(),
                        "status": (row.get("Status") or "").strip(),
                        "nonprofit_count": _to_int(row.get("IRS Nonprofit Count")) or 0,
                        "high_priority_count": _to_int(row.get("High-Priority Count")) or 0,
                        "funder_starter_count": _to_int(row.get("Funder Starter Count")) or 0,
                        "notes": (row.get("Build Notes") or "").strip(),
                    },
                )
                count += 1
        return count
