"""Phase 2 contact enrichment: website/phone/officer from full Form 990 e-file XML.

Route decision (probed 2026-07):
  A. IRS Form 990-series XML bulk downloads (apps.irs.gov/pub/epostcard/990/xml/
     <year>/<year>_TEOS_XML_<NN>.zip) — full e-filed returns. WebsiteAddressTxt,
     Filer/PhoneNum, BusinessOfficerGrp/{PersonNm,PhoneNum} are all present.
     ~100-500 MB per zip, ~4 GB per year; zips are downloaded one at a time into
     --irs-dir/xml/ and DELETED after processing, so peak disk use is one zip.
     CHOSEN as the primary (and only functional) route.
  B. ProPublica Nonprofit Explorer API — probed: the organization object carries
     NO website/phone/officer fields (only registry + financial extract data),
     so --route propublica is rejected with an explanatory error.

Usage:
    DEBUG=1 .venv/bin/python manage.py fetch_990_contacts
        [--priority High] [--route auto|xml|propublica]
        [--years 2026,2025,2024] [--limit N] [--no-resume] [--force]
        [--irs-dir data/florida-crm-staging/irs] [--keep-zips]

Behavior (mirrors enrich_florida_contacts conventions):
  * Loads the FloridaOrg EIN set for --priority up front (plus, opportunistically,
    ALL FloridaOrg EINs — any org encountered in the stream gets enriched; the
    priority set only drives the coverage report).
  * EINs normalized by stripping leading zeros on both sides of the join.
  * Newest tax year wins within this run (tracked in the progress file across
    resumes). contact_source stamped 'irs-990-xml-<taxyear>'.
  * NEVER overwrites a non-empty field whose contact_source is a different
    source family without --force. Same-family ('irs-990-xml-*') rows may be
    refreshed by a newer tax year.
  * Resumable: progress file --irs-dir/fetch_990_progress.json records processed
    zip names and per-EIN applied tax years; interrupted runs pick up at the
    next unprocessed zip (default on; --no-resume starts over).
"""

import json
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from openoutreach.funding.irs_xml import (
    BASE_URL, BUNDLE_SUFFIXES, download_bundle, iter_zip_xml_members,
)
from openoutreach.signals.models import FloridaOrg

DEFAULT_YEARS = "2026,2025,2024"
SOURCE_PREFIX = "irs-990-xml-"
PROGRESS_FILE = "fetch_990_progress.json"
BATCH = 2000
UPDATE_FIELDS = ["website", "phone", "principal_officer",
                 "contact_source", "contact_updated_at"]
_EIN_RE = re.compile(rb"<(?:\w+:)?EIN>(\d+)</")


def norm_ein(value):
    return (value or "").strip().lstrip("0")


def _clean_website(raw):
    value = (raw or "").strip()
    if not value or value.upper() in {"N/A", "NA", "NONE", "NO", "NO WEBSITE", "NULL"}:
        return ""
    if "@" in value or " " in value or "." not in value:
        return ""
    if not value.lower().startswith(("http://", "https://")):
        value = "http://" + value
    return value[:500]


def _clean_phone(raw):
    value = re.sub(r"\D", "", (raw or ""))
    return value[:40] if len(value) >= 7 else ""


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def parse_990_xml(data):
    """Parse one e-file return XML (bytes) -> dict or None.

    Returns {ein, tax_year, website, phone, officer} with '' for missing
    values. Namespace-agnostic (matches on local tag names).
    """
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return None
    ein = tax_year = filer_phone = officer = officer_phone = website = ""
    for el in root.iter():
        tag = _local(el.tag)
        text = (el.text or "").strip()
        if tag == "Filer":
            for sub in el.iter():
                t, v = _local(sub.tag), (sub.text or "").strip()
                if t == "EIN" and v and not ein:
                    ein = v
                elif t == "PhoneNum" and v and not filer_phone:
                    filer_phone = v
        elif tag == "BusinessOfficerGrp":
            for sub in el:
                t, v = _local(sub.tag), (sub.text or "").strip()
                if t == "PersonNm" and v and not officer:
                    officer = v
                elif t == "PhoneNum" and v and not officer_phone:
                    officer_phone = v
        elif not text:
            continue
        elif tag == "TaxYr" and not tax_year:
            tax_year = text
        elif tag == "WebsiteAddressTxt" and not website:
            website = text
    phone = filer_phone or officer_phone
    if not officer:
        for el in root.iter():
            if _local(el.tag) in ("PrincipalOfficerNm", "PrincipalOfcrBusinessName") \
                    and (el.text or "").strip():
                officer = el.text.strip()
                break
    if not ein:
        return None
    try:
        year = int(tax_year)
    except ValueError:
        year = 0
    return {
        "ein": norm_ein(ein),
        "tax_year": year,
        "website": _clean_website(website),
        "phone": _clean_phone(phone),
        "officer": officer.strip()[:200],
    }


def _source_year(source):
    """Tax year embedded in an 'irs-990-xml-<year>' contact_source, else None."""
    if source and source.startswith(SOURCE_PREFIX):
        try:
            return int(source[len(SOURCE_PREFIX):])
        except ValueError:
            return None
    return None


def apply_extract(org, extract, *, force=False):
    """Apply one parsed return to a FloridaOrg (no save). Returns True if changed.

    No-overwrite rule: a non-empty field is only replaced when --force, or when
    the row's existing contact_source is in the same 'irs-990-xml-*' family with
    a tax year <= this extract's (newest tax year wins within the family).
    """
    source = f"{SOURCE_PREFIX}{extract['tax_year']}"
    prev_year = _source_year(org.contact_source)
    same_family_newer = prev_year is not None and extract["tax_year"] >= prev_year
    changed = False
    for field, value in (("website", extract["website"]),
                         ("phone", extract["phone"]),
                         ("principal_officer", extract["officer"])):
        if not value:
            continue
        current = getattr(org, field)
        if current == value:
            continue
        if current and not force and not same_family_newer:
            continue  # never clobber a non-empty different-source value
        setattr(org, field, value)
        changed = True
    if changed:
        org.contact_source = source
        org.contact_updated_at = timezone.now()
    return changed


class Command(BaseCommand):
    help = ("Enrich FloridaOrg website/phone/principal_officer from IRS Form 990 "
            "e-file XML bulk downloads (route A; see module docstring).")

    def add_arguments(self, parser):
        parser.add_argument("--priority", default="High")
        parser.add_argument("--route", default="auto",
                            choices=["auto", "xml", "propublica"])
        parser.add_argument("--years", default=DEFAULT_YEARS,
                            help="Comma-separated download years, newest first.")
        parser.add_argument("--limit", type=int, default=0,
                            help="Stop after this many priority-tier EINs updated (testing).")
        parser.add_argument("--no-resume", action="store_true",
                            help="Ignore the progress file and reprocess all zips.")
        parser.add_argument("--force", action="store_true",
                            help="Overwrite non-empty different-source values.")
        parser.add_argument("--irs-dir", default="data/florida-crm-staging/irs")
        parser.add_argument("--keep-zips", action="store_true",
                            help="Do not delete zips after processing.")

    # ---- coverage helpers -------------------------------------------------
    def _coverage(self, priority):
        tier = FloridaOrg.objects.filter(priority=priority)
        return {
            "tier_total": tier.count(),
            "tier_website": tier.exclude(website="").count(),
            "tier_phone": tier.exclude(phone="").count(),
            "tier_officer": tier.exclude(principal_officer="").count(),
            "all_website": FloridaOrg.objects.exclude(website="").count(),
            "all_phone": FloridaOrg.objects.exclude(phone="").count(),
            "all_officer": FloridaOrg.objects.exclude(principal_officer="").count(),
        }

    def handle(self, *args, **options):
        if options["route"] == "propublica":
            raise CommandError(
                "ProPublica route probed 2026-07: the /api/v2/organizations/"
                "<ein>.json object has no website/phone/officer fields, so it "
                "cannot serve this enrichment. Use --route xml (or auto)."
            )
        priority = options["priority"]
        irs_dir = Path(options["irs_dir"])
        xml_dir = irs_dir / "xml"
        xml_dir.mkdir(parents=True, exist_ok=True)
        progress_path = irs_dir / PROGRESS_FILE

        progress = {"processed_zips": [], "applied_years": {}}
        if progress_path.exists() and not options["no_resume"]:
            progress = json.loads(progress_path.read_text())
        applied_years = progress["applied_years"]  # ein -> newest tax year applied

        # EIN universes: all orgs (opportunistic) + the priority tier (reporting/limit).
        ein_to_pks, tier_eins = {}, set()
        for pk, ein, pri in FloridaOrg.objects.values_list("pk", "ein", "priority"):
            key = norm_ein(ein)
            if not key:
                continue
            ein_to_pks.setdefault(key, []).append(pk)
            if pri == priority:
                tier_eins.add(key)
        self.stdout.write(
            f"Targets: {len(tier_eins):,} {priority}-tier EINs "
            f"({len(ein_to_pks):,} total FloridaOrg EINs, enriched opportunistically)."
        )
        before = self._coverage(priority)

        years = [y.strip() for y in options["years"].split(",") if y.strip()]
        limit = options["limit"]
        force = options["force"]
        tier_updated = set()
        total_updated = 0

        for year in years:
            for suffix in BUNDLE_SUFFIXES:
                name = f"{year}_TEOS_XML_{suffix}.zip"
                if name in progress["processed_zips"]:
                    continue
                url = f"{BASE_URL}/{year}/{name}"
                zip_path = xml_dir / name
                if zip_path.exists() and not zipfile.is_zipfile(zip_path):
                    zip_path.unlink()  # stale HTML error page from a prior run
                if not zip_path.exists():
                    if not self._download(url, zip_path):
                        progress["processed_zips"].append(name)  # absent/empty bundle
                        self._save_progress(progress_path, progress)
                        continue
                n = self._process_zip(zip_path, ein_to_pks, tier_eins, applied_years,
                                      tier_updated, force=force)
                total_updated += n
                progress["processed_zips"].append(name)
                self._save_progress(progress_path, progress)
                if not options["keep_zips"]:
                    zip_path.unlink(missing_ok=True)
                self.stdout.write(
                    f"  {name}: {n:,} org rows updated "
                    f"({len(tier_updated):,} {priority}-tier EINs touched so far)"
                )
                if limit and len(tier_updated) >= limit:
                    self.stdout.write(f"--limit {limit} reached; stopping.")
                    self._report(priority, before)
                    return
        self._report(priority, before)

    # ---- plumbing ---------------------------------------------------------
    def _save_progress(self, path, progress):
        path.write_text(json.dumps(progress))

    def _download(self, url, dest):
        """Download url -> dest. Returns False if missing/empty (skippable)."""
        return download_bundle(url, dest, log=self.stdout.write)

    def _iter_xml_members(self, zip_path, ein_to_pks):
        """Yield raw XML bytes for members whose Filer EIN is a FloridaOrg EIN.

        Shared streaming machinery lives in ``funding/irs_xml.py``; this wraps
        it with a head-bytes EIN prefilter so only FloridaOrg returns are read.
        """

        def _is_florida_org(head):
            m = _EIN_RE.search(head)
            return bool(m) and norm_ein(m.group(1).decode()) in ein_to_pks

        yield from iter_zip_xml_members(
            zip_path, head_filter=_is_florida_org, log=self.stderr.write,
        )

    def _process_zip(self, zip_path, ein_to_pks, tier_eins, applied_years,
                     tier_updated, *, force):
        """Stream one bundle; parse only members whose EIN is a FloridaOrg EIN."""
        extracts = {}  # ein -> best extract in this zip
        for data in self._iter_xml_members(zip_path, ein_to_pks):
            extract = parse_990_xml(data)
            if extract is None or extract["ein"] not in ein_to_pks:
                continue
            ein = extract["ein"]
            if ein in extracts and extracts[ein]["tax_year"] >= extract["tax_year"]:
                continue
            if applied_years.get(ein, -1) >= extract["tax_year"]:
                continue  # already applied same/newer year in this run
            extracts[ein] = extract

        if not extracts:
            return 0
        updated = 0
        pks = [pk for ein in extracts for pk in ein_to_pks[ein]]
        to_update = []
        for org in FloridaOrg.objects.filter(pk__in=pks).iterator(chunk_size=BATCH):
            extract = extracts[norm_ein(org.ein)]
            if apply_extract(org, extract, force=force):
                to_update.append(org)
                updated += 1
                if norm_ein(org.ein) in tier_eins:
                    tier_updated.add(norm_ein(org.ein))
                if len(to_update) >= BATCH:
                    FloridaOrg.objects.bulk_update(to_update, UPDATE_FIELDS,
                                                   batch_size=BATCH)
                    to_update = []
        if to_update:
            FloridaOrg.objects.bulk_update(to_update, UPDATE_FIELDS, batch_size=BATCH)
        for ein, extract in extracts.items():
            applied_years[ein] = max(applied_years.get(ein, -1), extract["tax_year"])
        return updated

    def _report(self, priority, before):
        after = self._coverage(priority)
        self.stdout.write(self.style.SUCCESS("Coverage (before -> after):"))
        rows = [
            (f"{priority} tier website", "tier_website"),
            (f"{priority} tier phone", "tier_phone"),
            (f"{priority} tier officer", "tier_officer"),
            ("All orgs website", "all_website"),
            ("All orgs phone", "all_phone"),
            ("All orgs officer", "all_officer"),
        ]
        total = before["tier_total"]
        for label, key in rows:
            pct = f" ({after[key] / total:.1%} of {total:,})" if key.startswith("tier") else ""
            self.stdout.write(f"  {label:24s} {before[key]:>7,} -> {after[key]:>7,}{pct}")
