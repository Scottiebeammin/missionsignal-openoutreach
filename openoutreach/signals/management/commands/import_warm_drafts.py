"""
Load Marcus's hand-written warm emails (day-file drafts) onto the warm SalesLeads
so the Outreach Cockpit shows HIS emails, not the generic composed template.

Reads data/warm-email-drafts.json (extracted from the vault day1–13 FINAL files)
and matches each to a warm lead BY EMAIL — exact and safe, no fuzzy guessing, no
lead creation (that risked duplicates). Sets the lead's subject + draft, and
restores the addressee NAME to the contact Marcus actually wrote to (the old CSV
import often stored a different/garbled name — e.g. "Trip Snelson" for a draft
addressed to "Madison Woodard", or "Hessemer, David" for "David Hessemer"). Never
overwrites a lead already marked sent. Emails with no matching lead are listed so
Marcus can handle them by hand (usually he wrote to a different contact than the
lead has, or the org isn't in his list yet).

    python manage.py import_warm_drafts
    python manage.py import_warm_drafts --dry-run
    python manage.py import_warm_drafts --show-unmatched
"""
import json

from django.core.management.base import BaseCommand, CommandError

from openoutreach.signals.models import SalesLead

DATA = "data/warm-email-drafts.json"


class Command(BaseCommand):
    help = "Load hand-written warm emails onto warm leads' drafts by email match (cockpit shows Marcus's version)."

    def add_arguments(self, parser):
        parser.add_argument("--data", default=DATA)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--show-unmatched", action="store_true")

    def handle(self, *args, **options):
        try:
            records = json.loads(open(options["data"]).read())
        except OSError as exc:
            raise CommandError(f"Cannot read {options['data']}: {exc}")

        by_email = {
            l.email.strip().lower(): l
            for l in SalesLead.objects.filter(list_segment=SalesLead.Segment.WARM)
            if l.email
        }
        loaded = skipped_sent = renamed = 0
        unmatched = []
        for rec in records:
            lead = by_email.get(rec["email"].strip().lower())
            if lead is None:
                unmatched.append(rec)
                continue
            if lead.email_status == "sent":
                skipped_sent += 1
                continue
            fields = ["subject_line", "outreach_draft", "updated_at"]
            if not options["dry_run"]:
                lead.subject_line = rec["subject"][:255]
                lead.outreach_draft = rec["body"]
                # Restore the addressee to the contact Marcus actually wrote to.
                contact = (rec.get("contact") or "").strip()
                if contact and contact.lower() != (lead.name or "").strip().lower():
                    lead.name = contact[:200]
                    fields.append("name")
                    renamed += 1
                lead.save(update_fields=fields)
            loaded += 1

        tag = "[dry-run] " if options["dry_run"] else ""
        self.stdout.write(self.style.SUCCESS(
            f"{tag}{loaded} real emails loaded onto warm leads ({renamed} names restored to the original "
            f"addressee); {skipped_sent} skipped (already sent); "
            f"{len(unmatched)} not matched (different contact/email or org not a lead)."
        ))
        if options["show_unmatched"]:
            self.stdout.write("\nUnmatched (handle by hand):")
            for rec in unmatched:
                self.stdout.write(f"  {rec['email']:<40} {rec['org']}")
