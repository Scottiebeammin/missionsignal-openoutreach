"""
Free contact-email pass: visit each FloridaOrg's own website (homepage + one
contact-ish page) and extract a published contact email. Polite by design:
max 2 requests per site, 1.5s pause between sites, honest User-Agent, 10s
timeouts, resumable progress file. Never overwrites an existing email.

Usage:
    python manage.py scrape_contact_emails                 # High tier, resume on
    python manage.py scrape_contact_emails --priority all --limit 200
"""

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from django.core.management.base import BaseCommand
from django.utils import timezone

from openoutreach.signals.models import FloridaOrg

UA = {"User-Agent": "AnansiAtlas-contact-lookup/1.0 (+https://anansiatlas.com; info@anansiatlas.com)"}
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
CONTACT_HREF_RE = re.compile(r'href=["\']([^"\']*(?:contact|about|connect|reach)[^"\']*)["\']', re.I)
# junk inboxes / non-org domains we never want
BAD_LOCAL = ("noreply", "no-reply", "donotreply", "example", "sentry", "wixpress", "godaddy")
BAD_DOMAIN = ("example.", "sentry.", "wix.com", "godaddy.com", "squarespace.com", "wordpress.com",
              "png", "jpg", "jpeg", "gif", "webp", "svg")
PREFERRED_LOCAL = ("info", "contact", "office", "admin", "hello", "mail", "email")


def _fetch(url: str) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
        if "text/html" not in (resp.headers.get("Content-Type") or "text/html"):
            return ""
        return resp.read(1_000_000).decode("utf-8", "ignore")


def _score(email: str, site_domain: str) -> int:
    local, _, domain = email.lower().partition("@")
    score = 0
    if domain.endswith(site_domain) or site_domain.endswith(domain):
        score += 10  # their own domain beats gmail etc.
    if any(local.startswith(p) for p in PREFERRED_LOCAL):
        score += 5
    return score


def extract_email(html: str, site_domain: str) -> str:
    candidates = set()
    for m in EMAIL_RE.finditer(html):
        email = m.group(0).lower().strip(".")
        local, _, domain = email.partition("@")
        if any(b in local for b in BAD_LOCAL):
            continue
        if any(domain.endswith(b) or b in domain for b in BAD_DOMAIN):
            continue
        if len(email) > 254:
            continue
        candidates.add(email)
    if not candidates:
        return ""
    return max(candidates, key=lambda e: (_score(e, site_domain), -len(e)))


def contact_page_url(html: str, base_url: str) -> str:
    m = CONTACT_HREF_RE.search(html)
    if not m:
        return ""
    href = m.group(1)
    if href.startswith(("mailto:", "tel:", "#", "javascript:")):
        return ""
    return urllib.parse.urljoin(base_url, href)


class Command(BaseCommand):
    help = "Politely scrape published contact emails from FloridaOrg websites (never overwrites)."

    def add_arguments(self, parser):
        parser.add_argument("--priority", default="High", help="High|Medium|Low|all")
        parser.add_argument("--limit", type=int, default=0)
        parser.add_argument("--delay", type=float, default=1.5)
        parser.add_argument("--progress-file", default="data/florida-crm-staging/scrape_progress.json")

    def handle(self, *args, **options):
        qs = FloridaOrg.objects.exclude(website="").filter(contact_email="")
        if options["priority"].lower() != "all":
            qs = qs.filter(priority__iexact=options["priority"])
        qs = qs.order_by("pk")

        progress_path = Path(options["progress_file"])
        progress_path.parent.mkdir(parents=True, exist_ok=True)
        done = set()
        if progress_path.exists():
            done = set(json.loads(progress_path.read_text()).get("done_pks", []))

        total = qs.count()
        found = errors = visited = 0
        self.stdout.write(f"{total:,} orgs with websites and no email ({options['priority']} tier); "
                          f"{len(done):,} already visited in prior runs.")
        try:
            for org in qs.iterator():
                if org.pk in done:
                    continue
                if options["limit"] and visited >= options["limit"]:
                    break
                visited += 1
                site = org.website
                domain = urllib.parse.urlsplit(site).netloc.removeprefix("www.")
                email = ""
                try:
                    html = _fetch(site)
                    email = extract_email(html, domain)
                    if not email:
                        contact_url = contact_page_url(html, site)
                        if contact_url:
                            time.sleep(options["delay"] / 2)
                            email = extract_email(_fetch(contact_url), domain)
                except (urllib.error.URLError, TimeoutError, ConnectionError, OSError, ValueError):
                    errors += 1
                if email and not org.contact_email:  # never overwrite
                    org.contact_email = email[:254]
                    org.contact_source = (org.contact_source + " + " if org.contact_source else "") + "website-scrape"
                    org.contact_updated_at = timezone.now()
                    org.save(update_fields=["contact_email", "contact_source", "contact_updated_at"])
                    found += 1
                done.add(org.pk)
                if visited % 25 == 0:
                    progress_path.write_text(json.dumps({"done_pks": sorted(done)}))
                    self.stdout.write(f"  visited {visited:,}/{total:,} — emails found {found:,} (errors {errors:,})")
                time.sleep(options["delay"])
        finally:
            progress_path.write_text(json.dumps({"done_pks": sorted(done)}))
        self.stdout.write(self.style.SUCCESS(
            f"Done. Visited {visited:,} sites: {found:,} emails found, {errors:,} unreachable."
        ))
