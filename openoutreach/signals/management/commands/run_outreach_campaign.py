"""The autonomous outreach runner — SHADOW MODE only in this build.

Decides exactly what the system would send, when, and why — and delivers
nothing. Every invocation follows the full operating order (ingest → freshness
→ gates → eligibility → validation → pacing) and records one auditable
decision per lead as RunnerDecision rows, reviewable in the cockpit at
/operator/runner/.

    python manage.py run_outreach_campaign                # shadow, the default
    python manage.py run_outreach_campaign --shadow       # same, explicit
    python manage.py run_outreach_campaign --assume-fresh # shadow diagnostic (see below)

LIVE MODE IS NOT ENABLED IN THIS BUILD. ``--live`` refuses unconditionally:
the shadow phase exists to validate that the runner makes the decisions Marcus
would, and delivery is a later, deliberate feature behind
OUTREACH_AUTOSEND_ENABLED (default false) — which nothing in this build honors
even when set.

Shadow mode's writes are RunnerDecision rows and nothing else: no SENT, no
SENDING, no sent_at, no lead state, no outcome, no follow-up clock, no consumed
capacity. It also generates no drafts — drafting stays in preview_cohort_drafts
(one prompt path, human-reviewed batches); leads whose draft is missing or
stale are reported as NEEDS_DRAFT rather than silently drafted with money.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone


class Command(BaseCommand):
    help = "Evaluate the cold campaign and record what WOULD be sent. Shadow only — delivers nothing."

    def add_arguments(self, parser):
        parser.add_argument("--shadow", action="store_true", default=False,
                            help="Decision-only mode (the default — passing it is just explicit).")
        parser.add_argument("--live", action="store_true", default=False,
                            help="Refused in this build. Live delivery is a later, deliberate feature.")
        parser.add_argument("--segment", default="cold_florida_crm",
                            help="Lead segment to evaluate (default: cold_florida_crm).")
        parser.add_argument("--skip-ingest", action="store_true", default=False,
                            help="Skip the inbound poll (freshness is still enforced from stored "
                                 "cursor state — this saves the Gmail round-trip, not the invariant).")
        parser.add_argument("--assume-fresh", action="store_true", default=False,
                            help="SHADOW DIAGNOSTIC ONLY: evaluate as if mailboxes were fresh, for "
                                 "inspecting decisions before the Google mailbox setup exists. "
                                 "Ignored — refused — outside shadow mode; the live path will have "
                                 "no equivalent.")

    def handle(self, *args, **options):
        from openoutreach.signals import runner
        from openoutreach.signals.gmail_transport import (
            GmailNotConfigured,
            GmailTransport,
            configured_mailboxes,
            reply_mailbox,
        )
        from openoutreach.signals.ingest import ingest_mailbox
        from openoutreach.signals.models import RunnerDecision

        if options["live"]:
            # Fail closed, unconditionally. Not gated on OUTREACH_AUTOSEND_ENABLED:
            # this build contains no delivery path for the flag to enable, and a
            # refusal that could be env-toggled would be a backdoor.
            raise CommandError(
                "Live autonomous sending is not enabled in this build. The runner is in "
                "its shadow-validation phase: run without --live (or with --shadow) to "
                "record what would be sent. Delivery becomes possible only in a future "
                "build, behind OUTREACH_AUTOSEND_ENABLED, after shadow decisions are "
                "validated.")

        now = timezone.now()
        run_id = now.strftime("%Y%m%d-%H%M%S")

        # ── 1. inbound first — the runner enforces the order itself ──────────
        if not options["skip_ingest"]:
            boxes = configured_mailboxes()
            if not boxes:
                self.stdout.write(self.style.WARNING(
                    "No inbound mailboxes configured — nothing to ingest. Freshness "
                    "will hold unless --assume-fresh."))
            owner = reply_mailbox()
            for mailbox in boxes:
                try:
                    transport = GmailTransport(mailbox)
                except GmailNotConfigured as exc:
                    self.stderr.write(self.style.WARNING(f"{mailbox}: {exc}"))
                    continue
                stats = ingest_mailbox(transport, mailbox=mailbox, owner=owner)
                self.stdout.write(f"ingested {mailbox}: fetched {stats.fetched}, "
                                  f"stored {stats.stored}, errors {stats.errors}")
                if stats.errors:
                    # A failed poll means reply visibility is not current. Stop
                    # before evaluating anything — the freshness gate would hold
                    # anyway (last_error is set), but stopping here says why.
                    self.stderr.write(self.style.ERROR(
                        f"{mailbox}: ingestion failed — the cursor was held and "
                        "sending must not be evaluated against stale reply state. "
                        "Stopping."))
                    RunnerDecision.objects.create(
                        run_id=run_id, mode="shadow", code=runner.HOLD_MAILBOX_STALE,
                        reason=f"ingestion failed for {mailbox} this run", created_at=now)
                    return

        # ── 2–6. freshness → gates → eligibility → validation → pacing ───────
        result = runner.evaluate_campaign(
            segment=options["segment"], now=now,
            assume_fresh=options["assume_fresh"])

        if options["assume_fresh"]:
            self.stdout.write(self.style.WARNING(
                "--assume-fresh: mailbox freshness NOT verified this run — decisions "
                "below are diagnostic, not send-grade."))

        # ── 7. record — shadow's only write ──────────────────────────────────
        rows = [
            RunnerDecision(
                run_id=run_id, mode="shadow", lead=d.lead, outreach_message=d.message,
                code=d.code, reason=d.reason,
                would_send_subject=(d.message.subject[:300]
                                    if d.message is not None and d.code in runner.CANDIDATE_CODES
                                    else ""),
                created_at=now)
            for d in result.decisions
        ]
        RunnerDecision.objects.bulk_create(rows)

        for d in result.decisions:
            who = (f"#{d.lead.pk} {d.lead.organization or d.lead.name}"
                   if d.lead is not None else "(system)")
            line = f"{d.code:24} {who} — {d.reason}"
            if d.code in runner.CANDIDATE_CODES:
                self.stdout.write(self.style.SUCCESS(line))
            elif d.code.startswith("HOLD"):
                self.stdout.write(self.style.WARNING(line))
            else:
                self.stdout.write(line)

        counts = result.counts()
        cap = runner.daily_send_limit()
        sent_today = runner.sends_today(now)
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"run {run_id} (shadow) — {len(result.decisions)} decision(s): "
            + ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))))
        self.stdout.write(
            f"pacing: {sent_today}/{cap} sent today, "
            f"min {runner.min_seconds_between_sends()}s between sends — "
            f"{len(result.candidates())} candidate(s) fit this run")
        self.stdout.write(self.style.SUCCESS(
            "Nothing was sent, claimed, or advanced. Review at /operator/runner/."))
