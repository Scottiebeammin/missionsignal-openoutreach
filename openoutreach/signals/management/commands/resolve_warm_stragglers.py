"""
Resolve the 8 hand-written warm emails that import_warm_drafts couldn't match by
email (curated with Marcus on 2026-07-05).

- 2 orgs are already in the pipeline under a DIFFERENT contact than Marcus wrote
  to. Per his call, keep BOTH: the person the email addresses becomes the primary
  recipient, the existing lead's contact is CC'd, and the draft attaches.
- 6 orgs aren't in the pipeline at all; create a warm lead so the email shows in
  the cockpit.

Bodies/subjects are read from data/warm-email-drafts.json. Idempotent; never
touches a sent lead. Run after import_warm_drafts:

    python manage.py resolve_warm_stragglers
"""
import json

from django.core.management.base import BaseCommand, CommandError

from openoutreach.signals.models import SalesLead

DRAFT_JSON = "data/warm-email-drafts.json"

# Already in the pipeline under a different contact — keep both (primary + CC).
CC_MERGES = [
    {"draft_email": "info@8cents.org", "lead_email": "jsantiago@8cents.org", "name": "Lashea Reaves"},
    {"draft_email": "avargas@4cflorida.org", "lead_email": "jbyron@4cflorida.org", "name": "Admary Vargas"},
]

# Not in the pipeline — create a warm lead so the email shows in the cockpit.
CREATE = [
    {"email": "dofsowitz@hcc-offm.org", "org": "Hope CommUnity Center", "contact": "Debo Ofsowitz"},
    {"email": "kelly.astro@hfuw.org", "org": "Heart of Florida United Way", "contact": "Kelly Astro"},
    {"email": "msperzel@harborhousefl.com", "org": "Harbor House of Central Florida", "contact": "Michelle Sperzel"},
    {"email": "info@centralfloridachildrenshome.com", "org": "Central Florida Children's Home", "contact": ""},
    {"email": "mstahlman@mhacf.org", "org": "Mental Health Association of Central Florida", "contact": "Marni Stahlman"},
    {"email": "erushlow@rmhccf.org", "org": "Ronald McDonald House Charities of Central Florida", "contact": "Emily Rushlow"},
]


class Command(BaseCommand):
    help = "Resolve the 8 unmatched warm emails: CC-merge 2, create 6 (curated)."

    def handle(self, *args, **options):
        try:
            records = json.loads(open(DRAFT_JSON).read())
        except OSError as exc:
            raise CommandError(f"Cannot read {DRAFT_JSON}: {exc}")
        by_email = {r["email"].strip().lower(): r for r in records}

        merged = created = skipped = missing = 0

        for m in CC_MERGES:
            rec = by_email.get(m["draft_email"])
            lead = SalesLead.objects.filter(email__iexact=m["lead_email"], list_segment="warm").first()
            if not rec or not lead:
                self.stdout.write(self.style.WARNING(f"  merge skipped (no draft/lead): {m['draft_email']}"))
                missing += 1
                continue
            if lead.email_status == "sent":
                skipped += 1
                continue
            lead.name = m["name"]
            lead.email = m["draft_email"]          # who the email addresses = primary
            lead.cc_emails = m["lead_email"]        # keep the original contact on the thread
            lead.subject_line = rec["subject"][:255]
            lead.outreach_draft = rec["body"]
            lead.save(update_fields=["name", "email", "cc_emails", "subject_line", "outreach_draft", "updated_at"])
            merged += 1

        for c in CREATE:
            rec = by_email.get(c["email"])
            if not rec:
                self.stdout.write(self.style.WARNING(f"  create skipped (no draft): {c['email']}"))
                missing += 1
                continue
            lead, was_created = SalesLead.objects.get_or_create(
                email=c["email"], list_segment=SalesLead.Segment.WARM,
                defaults={
                    "name": c["contact"] or c["org"],
                    "organization": c["org"],
                    "warmth": SalesLead.Warmth.WARM,
                    "source": SalesLead.Source.WARM,
                    "status": SalesLead.Status.NEW,
                    "subject_line": rec["subject"][:255],
                    "outreach_draft": rec["body"],
                },
            )
            if not was_created and lead.email_status != "sent":
                lead.subject_line = rec["subject"][:255]
                lead.outreach_draft = rec["body"]
                lead.save(update_fields=["subject_line", "outreach_draft", "updated_at"])
            created += 1 if was_created else 0

        self.stdout.write(self.style.SUCCESS(
            f"Stragglers resolved: {merged} CC-merged (both contacts), {created} new leads created, "
            f"{skipped} skipped (sent), {missing} missing drafts. All 162 emails now in the cockpit."
        ))
