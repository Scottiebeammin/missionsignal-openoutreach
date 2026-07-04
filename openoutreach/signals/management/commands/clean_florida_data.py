"""Normalize FloridaOrg + SalesLead contact/display data in place.

Idempotent: a second run reports 0 changes. `--dry-run` prints per-field
change counts without writing.
"""

from django.core.management.base import BaseCommand

from openoutreach.signals.market import (
    clean_email,
    clean_phone,
    clean_website,
    clean_zip,
    derive_service_area,
    smart_title,
)
from openoutreach.signals.models import FloridaOrg, SalesLead

BATCH = 2000

ORG_FIELDS = [
    "name", "sort_name", "street", "city", "principal_officer",
    "phone", "website", "contact_email", "zip_code", "service_area",
]


def clean_org(org):
    """Mutate org in place; return list of changed field names."""
    changed = []

    for field in ("name", "sort_name", "street", "city", "principal_officer"):
        old = getattr(org, field)
        new = smart_title(old)
        if new != old:
            setattr(org, field, new)
            changed.append(field)

    new_phone = clean_phone(org.phone)
    if new_phone != org.phone:
        org.phone = new_phone
        changed.append("phone")

    raw_site = org.website
    new_site = clean_website(raw_site)
    if raw_site and "@" in raw_site and not new_site:
        # Website field actually holds an email — route it.
        candidate = clean_email(raw_site)
        if candidate and not org.contact_email:
            org.contact_email = candidate
            changed.append("contact_email")
    if new_site != raw_site:
        org.website = new_site
        changed.append("website")

    new_email = clean_email(org.contact_email)
    if new_email and new_email != org.contact_email:
        # Only rewrite when the cleaner produced a valid email; never blank.
        org.contact_email = new_email
        if "contact_email" not in changed:
            changed.append("contact_email")

    new_zip = clean_zip(org.zip_code)
    if new_zip != org.zip_code:
        org.zip_code = new_zip
        changed.append("zip_code")

    area = derive_service_area(org.ntee_code, org.ntee_sector, org.name)
    if area != org.service_area:
        org.service_area = area
        changed.append("service_area")

    return changed


def clean_lead(lead):
    """Mutate lead in place; return changed fields. Never blanks a value."""
    changed = []
    new_phone = clean_phone(lead.phone)
    if new_phone and new_phone != lead.phone:
        lead.phone = new_phone
        changed.append("phone")
    new_email = clean_email(lead.email)
    if new_email and new_email != lead.email:
        lead.email = new_email
        changed.append("email")
    return changed


class Command(BaseCommand):
    help = "Normalize FloridaOrg and SalesLead data (names, phones, websites, emails, ZIPs)."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Report changes without writing.")

    def handle(self, *args, **options):
        dry = options["dry_run"]
        counts = {}

        def bump(prefix, fields):
            for f in fields:
                counts[f"{prefix}.{f}"] = counts.get(f"{prefix}.{f}", 0) + 1

        org_rows = 0
        pending = []
        area_dist = {}
        for org in FloridaOrg.objects.all().iterator(chunk_size=BATCH):
            changed = clean_org(org)
            area_dist[org.service_area] = area_dist.get(org.service_area, 0) + 1
            if changed:
                org_rows += 1
                bump("FloridaOrg", changed)
                pending.append(org)
                if not dry and len(pending) >= BATCH:
                    FloridaOrg.objects.bulk_update(pending, ORG_FIELDS)
                    pending = []
        if not dry and pending:
            FloridaOrg.objects.bulk_update(pending, ORG_FIELDS)

        lead_rows = 0
        lead_pending = []
        for lead in SalesLead.objects.all().iterator(chunk_size=BATCH):
            changed = clean_lead(lead)
            if changed:
                lead_rows += 1
                bump("SalesLead", changed)
                lead_pending.append(lead)
        if not dry and lead_pending:
            SalesLead.objects.bulk_update(lead_pending, ["phone", "email"], batch_size=BATCH)

        mode = "DRY RUN — no writes" if dry else "applied"
        self.stdout.write(self.style.MIGRATE_HEADING(f"clean_florida_data ({mode})"))
        self.stdout.write(f"{'Field':<32}{'Changed rows':>12}")
        self.stdout.write("-" * 44)
        for key in sorted(counts):
            self.stdout.write(f"{key:<32}{counts[key]:>12,}")
        if not counts:
            self.stdout.write("(no changes — data already clean)")
        self.stdout.write("-" * 44)
        self.stdout.write(
            f"FloridaOrg rows touched: {org_rows:,} / {FloridaOrg.objects.count():,}   "
            f"SalesLead rows touched: {lead_rows:,} / {SalesLead.objects.count():,}"
        )
        self.stdout.write(self.style.MIGRATE_HEADING("Service-area distribution"))
        for area, n in sorted(area_dist.items(), key=lambda kv: -kv[1]):
            self.stdout.write(f"{area:<32}{n:>12,}")
