"""Shared IRS TEOS e-file XML bundle plumbing (download + member streaming).

The IRS publishes every e-filed 990-series return as yearly zip bundles at
https://apps.irs.gov/pub/epostcard/990/xml/<year>/<year>_TEOS_XML_<NN>.zip
(~100-500 MB each, ~4 GB per year). Two ingestion commands stream them:

  * ``signals/management/commands/fetch_990_contacts.py`` — FloridaOrg contact
    enrichment (website/phone/officer) from any 990-series return.
  * ``funding/management/commands/pull_990pf_grants.py`` — 990-PF Part XV
    grants-paid intelligence (FoundationGrantPaid rows).

Both share this module so the quirky parts live in one place: HEAD-less 404
probing of absent monthly bundles, Deflate64 members (compress_type 9,
unsupported by Python's ``zipfile`` — extracted via system ``unzip``), corrupt
central directories, and cheap head-bytes prefiltering so only interesting
members are read in full. Stdlib-only (urllib) by design — safe in the slim
``web.txt`` build.
"""

import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from django.core.management.base import CommandError

BASE_URL = "https://apps.irs.gov/pub/epostcard/990/xml"
# Known monthly bundle suffixes; missing/empty ones are skipped after a probe.
BUNDLE_SUFFIXES = [
    "01A", "02A", "03A", "04A", "05A", "05B", "06A", "07A", "08A",
    "09A", "10A", "11A", "11B", "11C", "12A",
]
_UA = "AnansiAtlas-research/1.0 (nonprofit contact enrichment)"


def bundle_name(year, suffix):
    return f"{year}_TEOS_XML_{suffix}.zip"


def bundle_url(year, name):
    return f"{BASE_URL}/{year}/{name}"


def download_bundle(url, dest, *, log=lambda msg: None):
    """Download url -> dest (Path). Returns False if missing/empty (skippable)."""
    log(f"Downloading {url} ...")
    tmp = dest.with_suffix(".part")
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp, open(tmp, "wb") as fh:  # noqa: S310
            while True:
                chunk = resp.read(1 << 20)
                if not chunk:
                    break
                fh.write(chunk)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return False
        raise
    if tmp.stat().st_size == 0 or not zipfile.is_zipfile(tmp):
        tmp.unlink()  # empty/placeholder bundle (or an HTML error page)
        return False
    tmp.rename(dest)
    return True


def iter_zip_xml_members(zip_path, *, head_filter=None, log=lambda msg: None):
    """Yield raw XML bytes for members whose first 4 KB pass ``head_filter``.

    ``head_filter(head_bytes) -> bool`` prefilters members cheaply before the
    full member is read (None = yield every .xml member). Streams via zipfile
    when possible; IRS bundles that use Deflate64 (compress_type 9, unsupported
    by Python's zipfile) are extracted with the system ``unzip`` (Info-ZIP 6.0
    supports Deflate64) to a temp dir.
    """
    try:
        zf = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile:
        # Truncated/corrupt bundle (partial download or IRS HTML error page
        # that slipped past the download check) — skip it; the caller marks
        # it processed so resume doesn't crash-loop on the same file.
        log(f"  ! bad zip, skipping: {zip_path.name}")
        return
    with zf:
        deflate64 = any(i.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
                        for i in zf.infolist())
        if not deflate64:
            for info in zf.infolist():
                if not info.filename.lower().endswith(".xml"):
                    continue
                with zf.open(info) as fh:
                    head = fh.read(4096)
                    if head_filter is not None and not head_filter(head):
                        continue
                    yield head + fh.read()
            return
    tmp = Path(tempfile.mkdtemp(prefix="irs990_", dir=zip_path.parent))
    try:
        # IRS bundles have a quirky central directory ("-76 bytes too
        # long"); unzip extracts everything but exits 1-3 with warnings,
        # so judge success by what landed on disk, not the exit code.
        result = subprocess.run(  # noqa: S603
            ["unzip", "-q", "-o", str(zip_path), "-d", str(tmp)],
            capture_output=True, text=True)
        xml_files = [p for p in tmp.rglob("*")
                     if p.is_file() and p.suffix.lower() == ".xml"]
        if not xml_files:
            raise CommandError(
                f"unzip failed on {zip_path} (exit {result.returncode}): "
                f"{result.stderr[-500:]}"
            )
        for path in xml_files:
            with open(path, "rb") as fh:
                head = fh.read(4096)
                if head_filter is not None and not head_filter(head):
                    continue
                yield head + fh.read()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
