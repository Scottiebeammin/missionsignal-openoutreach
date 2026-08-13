"""The autonomous outreach runner — SHADOW MODE only in this build.

Decides exactly what the system would send, when, and why — and delivers
nothing. Every invocation follows the full operating order (ingest → freshness
→ gates → eligibility → validation → pacing) and records one auditable
decision per lead as RunnerDecision rows, reviewable in the cockpit at
/operator/runner/.

    python manage.py run_outreach_campaign                # shadow, the default
    python manage.py run_outreach_campaign --shadow       # same, explicit
    python manage.py run_outreach_campaign --assume-fresh # shadow diagnostic (see below)
    python manage.py run_outreach_campaign --live         # Gap 4B — DOUBLE-GATED

Live delivery is double-gated: it requires BOTH the explicit ``--live`` flag
AND ``OUTREACH_AUTOSEND_ENABLED=true`` in the environment (missing = false =
delivery impossible). Production keeps the flag unset until the controlled
canary (docs/outreach-live-canary.md). Live mode refuses --assume-fresh and
--skip-ingest outright — real freshness or no sends — and shares candidate
selection with shadow verbatim: the only difference is what happens after a
candidate is identified (atomic claim → final deterministic gate → SMTP
outside any transaction → finalize; small batch per invocation, spacing from
persisted state, no sleeps).

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

        live = options["live"]
        if live:
            # Double gate: the flag alone is not enough, the env alone is not
            # enough. Missing env = false = autonomous SMTP delivery impossible.
            if not runner.autosend_enabled():
                raise CommandError(
                    "Live autonomous sending is not enabled: OUTREACH_AUTOSEND_ENABLED "
                    "is unset or false. Shadow mode remains available without --live. "
                    "Enabling live delivery is a deliberate act — see "
                    "docs/outreach-live-canary.md for the required canary procedure.")
            if options["assume_fresh"] or options["skip_ingest"]:
                raise CommandError(
                    "--live cannot be combined with --assume-fresh or --skip-ingest: "
                    "live sending requires genuinely current inbound visibility, not "
                    "an assumption of it.")

        now = timezone.now()
        run_id = now.strftime("%Y%m%d-%H%M%S")
        mode = "live" if live else "shadow"

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
                        run_id=run_id, mode=mode, code=runner.HOLD_MAILBOX_STALE,
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

        # ── 7. record the evaluation — shadow's only write ───────────────────
        rows = [
            RunnerDecision(
                run_id=run_id, mode=mode, lead=d.lead, outreach_message=d.message,
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

        # ── 8. LIVE only: small batch, spaced, claimed, finally-gated ────────
        if live:
            self._execute_live(result, run_id=run_id)

        counts = result.counts()
        cap = runner.daily_send_limit()
        consumed = runner.capacity_consumed_today()
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"run {run_id} ({mode}) — {len(result.decisions)} decision(s): "
            + ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))))
        self.stdout.write(
            f"pacing: {consumed}/{cap} capacity consumed today, "
            f"min {runner.min_seconds_between_sends()}s between sends, "
            f"max {runner.max_sends_per_run()}/run — "
            f"{len(result.candidates())} candidate(s) identified")
        if not live:
            self.stdout.write(self.style.SUCCESS(
                "Nothing was sent, claimed, or advanced. Review at /operator/runner/."))

    def _execute_live(self, result, *, run_id: str) -> None:
        """Deliver at most max_sends_per_run candidates, spacing-gated from
        persisted state, each through claim → final gate → SMTP → finalize.
        Exits promptly — spacing not yet elapsed means stop, never sleep."""
        from django.utils import timezone

        from openoutreach.signals import runner
        from openoutreach.signals.models import RunnerDecision

        held = runner.hold_stuck_claims()
        if held:
            self.stderr.write(self.style.WARNING(
                f"{held} stuck SENDING claim(s) converted to held-AMBIGUOUS — "
                "review before any retry."))
        sent_this_run = 0
        for d in result.candidates():
            if sent_this_run >= runner.max_sends_per_run():
                self.stdout.write(f"batch limit ({runner.max_sends_per_run()}/run) "
                                  "reached — remaining candidates wait for the next run")
                break
            wait = runner.spacing_wait_seconds()
            if wait > 0:
                RunnerDecision.objects.create(
                    run_id=run_id, mode="live", lead=d.lead, outreach_message=d.message,
                    code=runner.SKIP_SPACING,
                    reason=f"minimum spacing not elapsed ({int(wait)}s remaining) — "
                           "the next cron invocation retries")
                self.stdout.write(f"spacing: {int(wait)}s remaining — stopping this run")
                break
            code, detail = runner.autonomous_send(d.message)
            RunnerDecision.objects.create(
                run_id=run_id, mode="live", lead=d.lead, outreach_message=d.message,
                code=code, reason=detail,
                would_send_subject=(d.message.subject or "")[:300],
                created_at=timezone.now())
            line = f"{code:24} #{d.lead.pk} {d.lead.organization or d.lead.name} — {detail}"
            if code == runner.LIVE_SENT:
                sent_this_run += 1
                self.stdout.write(self.style.SUCCESS(line))
            else:
                self.stderr.write(self.style.WARNING(line))
            if code == runner.LIVE_AMBIGUOUS:
                # Delivery state unknown — stop the whole run rather than keep
                # mailing through a failing connection.
                self.stderr.write(self.style.ERROR(
                    "ambiguous SMTP outcome — stopping this run; the message is held "
                    "for human verification and will not be auto-retried."))
                break
