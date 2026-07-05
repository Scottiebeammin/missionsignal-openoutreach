"""
Move the mined 990-PF foundation grants between environments.

    python manage.py foundation_snapshot export   # -> data/foundation-grants-snapshot.csv.gz
    python manage.py foundation_snapshot import    # <- same file (idempotent on dedup_key)

Export on the laptop (where the full IRS pull already ran), commit the gz, deploy,
then import once in the Render shell — far faster and lighter than re-running
pull_990pf_grants on a small production box. After importing, derive the funder
profiles with:

    python manage.py pull_990pf_grants --skip-pull --derive-funders

(That aggregates the imported grants into Funder rows without any download.)
"""
import csv
import gzip

from django.core.management.base import BaseCommand, CommandError

from openoutreach.funding.models import FoundationGrantPaid

SNAPSHOT = "data/foundation-grants-snapshot.csv.gz"
FIELDS = [
    "filer_ein", "filer_name", "filer_city", "filer_state",
    "recipient_name", "recipient_ein", "recipient_city", "recipient_state",
    "amount", "purpose", "tax_year", "source_url", "dedup_key",
]
INT_FIELDS = {"amount"}  # amount is BigIntegerField; tax_year is a CharField (stays text)


class Command(BaseCommand):
    help = "Export/import the FoundationGrantPaid table as a portable snapshot (idempotent on dedup_key)."

    def add_arguments(self, parser):
        parser.add_argument("action", choices=["export", "import"])
        parser.add_argument("--snapshot", default=SNAPSHOT)

    def handle(self, *args, **options):
        if options["action"] == "export":
            self._export(options)
        else:
            self._import(options)

    def _export(self, options):
        n = 0
        with gzip.open(options["snapshot"], "wt", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(FIELDS)
            for g in FoundationGrantPaid.objects.all().iterator(chunk_size=5000):
                writer.writerow([getattr(g, f) if getattr(g, f) is not None else "" for f in FIELDS])
                n += 1
        self.stdout.write(self.style.SUCCESS(f"Exported {n:,} grants -> {options['snapshot']}"))

    def _import(self, options):
        try:
            fh = gzip.open(options["snapshot"], "rt", newline="")
        except OSError as exc:
            raise CommandError(f"Cannot open snapshot: {exc}")
        created = skipped = 0
        with fh:
            reader = csv.DictReader(fh)
            existing = set(FoundationGrantPaid.objects.values_list("dedup_key", flat=True))
            batch = []
            for row in reader:
                key = row.get("dedup_key", "")
                if not key or key in existing:
                    skipped += 1
                    continue
                existing.add(key)
                vals = {}
                for f in FIELDS:
                    v = row.get(f, "")
                    if f in INT_FIELDS:
                        vals[f] = int(v) if v not in ("", "None") else None
                    else:
                        vals[f] = v or ""
                batch.append(FoundationGrantPaid(**vals))
                created += 1
                if len(batch) >= 5000:
                    FoundationGrantPaid.objects.bulk_create(batch)
                    batch = []
            if batch:
                FoundationGrantPaid.objects.bulk_create(batch)
        self.stdout.write(self.style.SUCCESS(
            f"Import done: {created:,} grants created, {skipped:,} skipped (already present)."
        ))
        self.stdout.write("Next: python manage.py pull_990pf_grants --skip-pull --derive-funders")
