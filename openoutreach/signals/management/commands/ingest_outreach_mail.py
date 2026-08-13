"""Poll the configured Workspace mailbox(es) and ingest outreach-related mail.

The Gap 3B observer job. Run by Render cron (see render.yaml); safe to run as
often as wanted — ingestion is idempotent per (mailbox, gmail_id), and the
cursor only advances after a clean pass, so a failed run re-reads rather than
skips. This job OBSERVES email. It sends nothing, answers nothing, and cannot
modify the mailbox — the transport has no mutating operations.

    python manage.py ingest_outreach_mail            # poll all configured mailboxes
    python manage.py ingest_outreach_mail --mailbox marcus@anansiatlas.com
"""
from __future__ import annotations

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Ingest replies/bounces from the configured Workspace mailboxes (read-only)."

    def add_arguments(self, parser):
        parser.add_argument("--mailbox", action="append", default=[],
                            help="Poll only this mailbox (repeatable). Default: all configured.")

    def handle(self, *args, **options):
        from openoutreach.signals.gmail_transport import (
            GmailNotConfigured,
            GmailTransport,
            configured_mailboxes,
            reply_mailbox,
        )
        from openoutreach.signals.ingest import ingest_mailbox

        boxes = [b.strip().lower() for b in options["mailbox"]] or configured_mailboxes()
        if not boxes:
            # Not configured is a state, not an error — the cron may be deployed
            # before the Google setup is done, and it must not page anyone daily.
            self.stdout.write(self.style.WARNING(
                "No mailboxes configured (OUTREACH_REPLY_MAILBOX / OUTREACH_BOUNCE_MAILBOX "
                "unset) — nothing to poll."))
            return

        owner = reply_mailbox()  # "the human whose replies are outbound_human"
        total_errors = 0
        for mailbox in boxes:
            try:
                transport = GmailTransport(mailbox)
            except GmailNotConfigured as exc:
                self.stderr.write(self.style.WARNING(f"{mailbox}: {exc}"))
                continue
            stats = ingest_mailbox(transport, mailbox=mailbox, owner=owner)
            total_errors += stats.errors
            self.stdout.write(
                f"{mailbox}: fetched {stats.fetched} · stored {stats.stored} "
                f"(replies {stats.replies}, bounces {stats.bounces}, "
                f"autoresponders {stats.autoresponders}, own {stats.outbound_human}) · "
                f"duplicates {stats.duplicates} · skipped {stats.skipped_irrelevant} · "
                f"unresolved {stats.unresolved} · errors {stats.errors}")
        if total_errors:
            self.stderr.write(self.style.ERROR(
                f"{total_errors} error(s) — the affected cursor(s) were held, the next run re-reads."))
