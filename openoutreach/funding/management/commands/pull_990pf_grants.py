"""IRS 990-PF foundation grant ingestion (grounded discovery, Layer 1).

Streams the same yearly TEOS e-file XML bundles as ``fetch_990_contacts``
(shared machinery: ``funding/irs_xml.py``), keeps only 990-PF returns
(cheap head-bytes prefilter on the ReturnTypeCd), parses Part XV grants paid
(``foundation_intel.parse_990pf_grants``), and stores the Florida-relevant
ones (FL filer OR FL recipient) as ``FoundationGrantPaid`` rows deduped on
``dedup_key`` — re-runs skip existing rows.

Usage:
    DEBUG=1 .venv/bin/python manage.py pull_990pf_grants
        [--years 2024 2025 2026] [--suffixes 01A ...] [--limit N]
        [--no-resume] [--irs-dir data/florida-crm-staging/irs] [--keep-zips]
        [--derive-funders] [--skip-pull]

Resumable: progress file --irs-dir/990pf_progress.json records processed zip
names; interrupted runs pick up at the next unprocessed zip (default on;
--no-resume starts over). Bundles are downloaded one at a time and deleted
after processing (--keep-zips to keep). --limit stops after storing N grants
(testing) WITHOUT marking the in-flight bundle processed, so a later full run
re-covers it (dedup makes that free). --derive-funders runs
``foundation_intel.derive_foundation_funders`` afterwards (--skip-pull to run
only the derivation).
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand

from openoutreach.funding.foundation_intel import (
    derive_foundation_funders, parse_990pf_grants, store_grants,
)
from openoutreach.funding.irs_xml import (
    BUNDLE_SUFFIXES, bundle_name, bundle_url, download_bundle, iter_zip_xml_members,
)

DEFAULT_YEARS = ["2024", "2025", "2026"]
PROGRESS_FILE = "990pf_progress.json"
HEARTBEAT_EVERY = 20_000  # scanned members between progress prints


def _is_990pf_head(head):
    """True when the first 4 KB look like a 990-PF return (ReturnTypeCd)."""
    return b"990PF" in head


class Command(BaseCommand):
    help = ("Ingest IRS 990-PF Part XV grants paid (Florida-relevant) into "
            "FoundationGrantPaid, and optionally derive verified Funder rows.")

    def add_arguments(self, parser):
        parser.add_argument("--years", nargs="+", default=DEFAULT_YEARS,
                            help="Bundle download years (default: 2024 2025 2026).")
        parser.add_argument("--suffixes", nargs="+", default=BUNDLE_SUFFIXES,
                            help="Restrict to specific bundle suffixes (e.g. 01A) — testing.")
        parser.add_argument("--limit", type=int, default=0,
                            help="Stop after storing this many grants (testing).")
        parser.add_argument("--no-resume", action="store_true",
                            help="Ignore the progress file and reprocess all zips.")
        parser.add_argument("--irs-dir", default="data/florida-crm-staging/irs")
        parser.add_argument("--keep-zips", action="store_true",
                            help="Do not delete zips after processing.")
        parser.add_argument("--derive-funders", action="store_true",
                            help="Derive/refresh Funder rows from stored grants afterwards.")
        parser.add_argument("--skip-pull", action="store_true",
                            help="Skip the bundle pull (use with --derive-funders).")

    def handle(self, *args, **options):
        totals = {"created": 0, "skipped": 0, "returns": 0}
        if not options["skip_pull"]:
            self._pull(options, totals)
        if options["derive_funders"]:
            summary = derive_foundation_funders()
            self.stdout.write(self.style.SUCCESS(
                f"Funder derivation: {summary['created']} created, "
                f"{summary['updated']} updated "
                f"({summary['considered']} foundations with enough grants)."
            ))

    # ---- pull -------------------------------------------------------------
    def _pull(self, options, totals):
        irs_dir = Path(options["irs_dir"])
        xml_dir = irs_dir / "xml"
        xml_dir.mkdir(parents=True, exist_ok=True)
        progress_path = irs_dir / PROGRESS_FILE

        progress = {"processed_zips": []}
        if progress_path.exists() and not options["no_resume"]:
            progress = json.loads(progress_path.read_text())

        limit = options["limit"]
        for year in options["years"]:
            for suffix in options["suffixes"]:
                name = bundle_name(year, suffix)
                if name in progress["processed_zips"]:
                    continue
                url = bundle_url(year, name)
                zip_path = xml_dir / name
                if zip_path.exists() and not zip_path.stat().st_size:
                    zip_path.unlink()
                if not zip_path.exists():
                    if not download_bundle(url, zip_path, log=self.stdout.write):
                        progress["processed_zips"].append(name)  # absent/empty bundle
                        progress_path.write_text(json.dumps(progress))
                        continue
                finished = self._process_zip(zip_path, url, totals, limit)
                if finished:
                    progress["processed_zips"].append(name)
                    progress_path.write_text(json.dumps(progress))
                if not options["keep_zips"]:
                    zip_path.unlink(missing_ok=True)
                self.stdout.write(
                    f"  {name}: {totals['created']:,} grants stored so far "
                    f"({totals['skipped']:,} dupes, {totals['returns']:,} 990-PF returns)"
                )
                if limit and totals["created"] >= limit:
                    self.stdout.write(f"--limit {limit} reached; stopping "
                                      f"(bundle left unprocessed for the full run).")
                    return
        self.stdout.write(self.style.SUCCESS(
            f"Done: {totals['created']:,} grants stored, {totals['skipped']:,} dupes "
            f"skipped, {totals['returns']:,} 990-PF returns parsed."
        ))

    def _process_zip(self, zip_path, url, totals, limit):
        """Stream one bundle. Returns False when --limit cut it short."""
        scanned = 0
        for data in iter_zip_xml_members(
            zip_path, head_filter=_is_990pf_head, log=self.stderr.write,
        ):
            scanned += 1
            if scanned % HEARTBEAT_EVERY == 0:
                self.stdout.write(
                    f"    ... {scanned:,} 990-PF candidates scanned in "
                    f"{zip_path.name} ({totals['created']:,} grants stored)"
                )
            parsed = parse_990pf_grants(data)
            if parsed is None:
                continue
            totals["returns"] += 1
            counts = store_grants(parsed, source_url=url)
            totals["created"] += counts["created"]
            totals["skipped"] += counts["skipped"]
            if limit and totals["created"] >= limit:
                return False
        return True
