"""Bulk-enrich FloridaOrg contact info from free public IRS datasets (stdlib only).

Data source: IRS Form 990-N (e-Postcard) bulk download — the only free IRS bulk
file that carries contact fields (org website/email + principal officer name).
The SOI annual financial extracts (990/990-EZ/990-PF) were inspected and contain
NO website/phone/email columns, so they are not read.

Expected file (place in data/florida-crm-staging/irs/, or pass --download):
    data-download-epostcard.zip   containing data-download-epostcard.txt
    (pipe-delimited: EIN|tax_year|name|gross<=25k|terminated|period_begin|
     period_end|website_or_email|officer_name|officer_addr...|)

Download URL: https://apps.irs.gov/pub/epostcard/data-download-epostcard.zip

Usage:
    .venv/bin/python manage.py enrich_florida_contacts [--download] [--force]
        [--irs-dir data/florida-crm-staging/irs]

Behavior:
  * Loads the FloridaOrg EIN set first and only keeps matching rows (memory-safe).
  * EINs are normalized by stripping leading zeros on both sides of the join.
  * Keeps the newest tax-year row per EIN; a value with '@' goes to
    contact_email, otherwise to website.
  * Idempotent: never overwrites a non-empty field with a different-source
    value unless --force. contact_source is stamped 'irs-epostcard-<taxyear>',
    contact_updated_at = now.
"""

import urllib.request
import zipfile
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from openoutreach.signals.models import FloridaOrg

EPOSTCARD_ZIP = "data-download-epostcard.zip"
EPOSTCARD_TXT = "data-download-epostcard.txt"
EPOSTCARD_URL = "https://apps.irs.gov/pub/epostcard/data-download-epostcard.zip"
BATCH = 2000
CONTACT_FIELDS = ["website", "contact_email", "principal_officer"]


def norm_ein(value):
    return (value or "").strip().lstrip("0")


def _clean_url_or_email(raw):
    """Return (website, email) from the e-postcard website field."""
    value = (raw or "").strip()
    if not value or value.upper() in {"N/A", "NA", "NONE", "NO", "NO WEBSITE", "NULL"}:
        return "", ""
    if "@" in value and " " not in value:
        return "", value.lower()
    if " " in value or "." not in value:
        return "", ""  # junk like "not applicable"
    if not value.lower().startswith(("http://", "https://")):
        value = "http://" + value
    return value[:500], ""


class Command(BaseCommand):
    help = (
        "Enrich FloridaOrg website/email/principal_officer from the IRS 990-N "
        "e-Postcard bulk file. Expects data-download-epostcard.zip in --irs-dir "
        "(use --download to fetch it via urllib)."
    )

    def add_arguments(self, parser):
        parser.add_argument("--irs-dir", default="data/florida-crm-staging/irs")
        parser.add_argument("--download", action="store_true",
                            help=f"Download {EPOSTCARD_URL} into --irs-dir first.")
        parser.add_argument("--force", action="store_true",
                            help="Overwrite non-empty fields with different-source values.")

    def handle(self, *args, **options):
        irs_dir = Path(options["irs_dir"])
        zip_path = irs_dir / EPOSTCARD_ZIP
        if options["download"]:
            irs_dir.mkdir(parents=True, exist_ok=True)
            self.stdout.write(f"Downloading {EPOSTCARD_URL} ...")
            urllib.request.urlretrieve(EPOSTCARD_URL, zip_path)  # noqa: S310
        if not zip_path.exists():
            raise CommandError(
                f"{zip_path} not found. Download it with --download or manually "
                f"from {EPOSTCARD_URL}"
            )

        # 1. Load our EIN universe (normalized) once.
        ein_to_pks = {}
        for pk, ein in FloridaOrg.objects.values_list("pk", "ein"):
            key = norm_ein(ein)
            if key:
                ein_to_pks.setdefault(key, []).append(pk)
        self.stdout.write(f"Loaded {len(ein_to_pks):,} distinct FloridaOrg EINs.")

        # 2. Stream the e-postcard file, keep newest tax-year row per matching EIN.
        best = {}  # ein -> (tax_year, website, email, officer)
        rows = matched = 0
        with zipfile.ZipFile(zip_path) as zf, zf.open(EPOSTCARD_TXT) as fh:
            for line in fh:
                rows += 1
                parts = line.decode("utf-8", errors="replace").split("|")
                if len(parts) < 9:
                    continue
                ein = norm_ein(parts[0])
                if ein not in ein_to_pks:
                    continue
                matched += 1
                try:
                    tax_year = int(parts[1])
                except ValueError:
                    tax_year = 0
                prev = best.get(ein)
                if prev is not None and prev[0] >= tax_year:
                    continue
                website, email = _clean_url_or_email(parts[7])
                officer = parts[8].strip()[:200]
                best[ein] = (tax_year, website, email, officer)
        self.stdout.write(
            f"Scanned {rows:,} e-postcard rows; {matched:,} matched Florida EINs "
            f"({len(best):,} distinct orgs)."
        )

        # 3. Apply, respecting the no-overwrite rule.
        force = options["force"]
        now = timezone.now()
        update_fields = CONTACT_FIELDS + ["contact_source", "contact_updated_at"]
        to_update, enriched = [], 0
        qs = FloridaOrg.objects.filter(
            pk__in=[pk for ein in best for pk in ein_to_pks[ein]]
        ).iterator(chunk_size=BATCH)
        for org in qs:
            tax_year, website, email, officer = best[norm_ein(org.ein)]
            new = {"website": website, "contact_email": email,
                   "principal_officer": officer}
            source = f"irs-epostcard-{tax_year}"
            changed = False
            for field, value in new.items():
                if not value:
                    continue
                current = getattr(org, field)
                if current == value:
                    continue
                if current and not force and org.contact_source != source:
                    continue  # never clobber a non-empty different-source value
                setattr(org, field, value)
                changed = True
            if changed:
                org.contact_source = source
                org.contact_updated_at = now
                to_update.append(org)
                enriched += 1
                if len(to_update) >= BATCH:
                    FloridaOrg.objects.bulk_update(to_update, update_fields, batch_size=BATCH)
                    to_update = []
        if to_update:
            FloridaOrg.objects.bulk_update(to_update, update_fields, batch_size=BATCH)

        stats = FloridaOrg.objects.exclude(website="").count()
        self.stdout.write(self.style.SUCCESS(
            f"Done. {enriched:,} orgs updated this run. "
            f"Orgs with website now: {stats:,}."
        ))
