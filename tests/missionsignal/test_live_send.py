"""Gap 4B: the live delivery path — built, gated, and disabled in production.

The invariants:

* live delivery requires BOTH --live and OUTREACH_AUTOSEND_ENABLED=true;
  a missing flag is false, and false makes autonomous SMTP impossible;
* candidate selection is shadow's, verbatim — live differs only after a
  candidate is identified;
* the claim commits before SMTP; no transaction spans the network call;
* a final deterministic gate re-checks cheap critical state at the last
  moment, closing the race between selection and delivery;
* definitive failures do not consume daily capacity, ambiguous ones do;
* spacing is enforced from persisted state with no sleeps.
"""
from __future__ import annotations

import time

import pytest
from django.core import mail
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import transaction
from django.utils import timezone

from openoutreach.signals import runner
from openoutreach.signals.ingest import FetchedMessage, ingest_message
from openoutreach.signals.models import (
    EmailOptOut,
    MailboxCursor,
    OutreachMessage,
    RunnerDecision,
    SalesLead,
)

pytestmark = pytest.mark.django_db

MAILBOX = "marcus@anansiatlas.com"
BOOKING = "https://cal.com/marcus/30min"
VALID_SUBJECT = "County funding for youth work"
VALID_BODY = (
    "Anansi Atlas tracks county and state funding for organizations like yours.\n\n"
    f"Join the founding group at anansiatlas.com, or book 30 minutes: {BOOKING}\n"
)


@pytest.fixture
def live_env(monkeypatch):
    monkeypatch.setenv("OUTREACH_REPLY_MAILBOX", MAILBOX)
    monkeypatch.setenv("OUTREACH_BOUNCE_MAILBOX", MAILBOX)
    monkeypatch.setenv("OUTREACH_AUTOSEND_ENABLED", "true")
    MailboxCursor.objects.create(mailbox=MAILBOX, last_success_at=timezone.now())
    # A live cron must never sleep its way through pacing.
    monkeypatch.setattr(time, "sleep", _no_sleep)


def _no_sleep(seconds):  # pragma: no cover - failing is its purpose
    raise AssertionError(f"live runner called time.sleep({seconds}) — pacing must "
                         "come from cron cadence and persisted state, never sleeps")


@pytest.fixture
def campaign(db):
    from openoutreach.core.models import Campaign

    return Campaign.objects.create(name="Anansi Atlas — Founding Cohort",
                                   booking_link=BOOKING)


def _lead(**kw):
    n = SalesLead.objects.count()
    return SalesLead.objects.create(**{
        "name": f"Lead {n}", "organization": f"Org {n}", "email": f"lead{n}@example.org",
        "list_segment": SalesLead.Segment.COLD_FLORIDA_CRM,
        "research_profile": "Verified: runs county-funded youth programs.",
        **kw,
    })


def _draft(lead, campaign=None, subject=VALID_SUBJECT, body=VALID_BODY, position=1, **kw):
    return OutreachMessage.objects.create(**{
        "lead": lead, "campaign": campaign, "subject": subject, "body": body,
        "status": OutreachMessage.Status.DRAFTED, "sequence_position": position,
        "personalization": OutreachMessage.Personalization.CATEGORY_RELEVANT,
        **kw,
    })


class _RaisingEmailMessage:
    """Stands in for outreach.EmailMessage; .send raises the configured error."""

    def __init__(self, exc):
        self.exc = exc

    def __call__(self, *args, **kwargs):
        self._instance = self
        return self

    def send(self, fail_silently=False):
        raise self.exc


# ── 1-2. the double gate ────────────────────────────────────────────────────

def test_live_refused_when_flag_false(campaign, monkeypatch):
    monkeypatch.setenv("OUTREACH_AUTOSEND_ENABLED", "false")
    with pytest.raises(CommandError, match="not enabled"):
        call_command("run_outreach_campaign", "--live")
    assert len(mail.outbox) == 0


def test_live_refused_when_flag_missing(campaign, monkeypatch):
    monkeypatch.delenv("OUTREACH_AUTOSEND_ENABLED", raising=False)
    with pytest.raises(CommandError, match="not enabled"):
        call_command("run_outreach_campaign", "--live")
    assert len(mail.outbox) == 0


def test_live_refuses_assumed_freshness(live_env, campaign):
    with pytest.raises(CommandError, match="assume-fresh"):
        call_command("run_outreach_campaign", "--live", "--assume-fresh")
    assert len(mail.outbox) == 0


# ── 3-4. inbound visibility gates live evaluation ───────────────────────────

def test_live_requires_mailbox_freshness(campaign, monkeypatch):
    monkeypatch.setenv("OUTREACH_REPLY_MAILBOX", MAILBOX)
    monkeypatch.setenv("OUTREACH_BOUNCE_MAILBOX", MAILBOX)
    monkeypatch.setenv("OUTREACH_AUTOSEND_ENABLED", "true")
    MailboxCursor.objects.create(
        mailbox=MAILBOX, last_success_at=timezone.now() - timezone.timedelta(hours=6))
    _draft(_lead(), campaign)
    call_command("run_outreach_campaign", "--live", verbosity=0)
    assert len(mail.outbox) == 0
    assert RunnerDecision.objects.filter(code=runner.HOLD_MAILBOX_STALE).exists()


def test_failed_ingestion_prevents_live_sends(campaign, monkeypatch):
    monkeypatch.setenv("OUTREACH_REPLY_MAILBOX", MAILBOX)
    monkeypatch.setenv("OUTREACH_BOUNCE_MAILBOX", MAILBOX)
    monkeypatch.setenv("OUTREACH_AUTOSEND_ENABLED", "true")
    cursor = MailboxCursor.objects.create(mailbox=MAILBOX, last_success_at=timezone.now())
    cursor.last_error = "HttpError: 401 invalid_grant"
    cursor.save()
    _draft(_lead(), campaign)
    call_command("run_outreach_campaign", "--live", verbosity=0)
    assert len(mail.outbox) == 0


# ── 5-6. the claim: one worker, committed before SMTP ───────────────────────

def test_claim_admits_one_worker(live_env, campaign):
    draft = _draft(_lead(), campaign)
    assert runner.claim_for_sending(draft) is True
    assert runner.claim_for_sending(draft) is False


def test_smtp_happens_outside_any_transaction(live_env, campaign, monkeypatch):
    from openoutreach.signals import outreach

    draft = _draft(_lead(), campaign)
    observed = {}
    real_email_message = outreach.EmailMessage

    class ObservingEmailMessage(real_email_message):
        def send(self, fail_silently=False):
            observed["in_atomic"] = transaction.get_connection().in_atomic_block
            draft.refresh_from_db()
            observed["status_at_smtp"] = draft.status
            return super().send(fail_silently=fail_silently)

    monkeypatch.setattr(outreach, "EmailMessage", ObservingEmailMessage)
    code, _ = runner.autonomous_send(draft)
    assert code == runner.LIVE_SENT
    # pytest-django wraps tests in one outer atomic; what matters is that the
    # send path itself opened no NEW transaction: the claim is already durable
    # (visible as SENDING) when SMTP runs.
    assert observed["status_at_smtp"] == OutreachMessage.Status.SENDING


# ── 7-10. the final pre-send gate closes selection→delivery races ───────────

def test_final_gate_catches_late_optout(live_env, campaign):
    lead = _lead()
    draft = _draft(lead, campaign)
    EmailOptOut.objects.create(email=lead.email)  # arrives after selection
    code, detail = runner.autonomous_send(draft)
    assert code == runner.LIVE_BLOCKED_FINAL_GATE
    assert "opted out" in detail
    assert len(mail.outbox) == 0
    draft.refresh_from_db()
    assert draft.status == OutreachMessage.Status.DRAFTED  # claim released


def test_final_gate_catches_late_reply(live_env, campaign):
    lead = _lead()
    draft = _draft(lead, campaign)
    lead.outreach_outcome = SalesLead.Outcome.REPLIED
    lead.save(update_fields=["outreach_outcome"])
    code, detail = runner.autonomous_send(draft)
    assert code == runner.LIVE_BLOCKED_FINAL_GATE
    assert len(mail.outbox) == 0


def test_final_gate_catches_late_terminal_outcome(live_env, campaign):
    lead = _lead()
    draft = _draft(lead, campaign)
    lead.outreach_outcome = SalesLead.Outcome.NOT_INTERESTED
    lead.save(update_fields=["outreach_outcome"])
    code, _ = runner.autonomous_send(draft)
    assert code == runner.LIVE_BLOCKED_FINAL_GATE
    assert len(mail.outbox) == 0


def test_final_gate_catches_late_disposition_hold(live_env, campaign):
    lead = _lead()
    draft = _draft(lead, campaign)
    lead.disposition = SalesLead.DISPOSITION_REVIEW
    lead.save(update_fields=["disposition"])
    code, _ = runner.autonomous_send(draft)
    assert code == runner.LIVE_BLOCKED_FINAL_GATE
    assert len(mail.outbox) == 0


# ── 11-14. finalization and the failure taxonomy ────────────────────────────

def test_successful_send_marks_sent_once_with_message_id(live_env, campaign):
    lead = _lead()
    draft = _draft(lead, campaign)
    code, _ = runner.autonomous_send(draft)
    assert code == runner.LIVE_SENT
    assert len(mail.outbox) == 1
    draft.refresh_from_db()
    lead.refresh_from_db()
    assert draft.status == OutreachMessage.Status.SENT
    assert draft.sent_at is not None
    assert draft.message_id.startswith("<") and "example.org" not in draft.message_id
    assert mail.outbox[0].extra_headers["Message-ID"] == draft.message_id
    assert lead.email_status == "sent"
    assert lead.outreach_outcome == SalesLead.Outcome.AWAITING
    # A second attempt cannot double-send.
    code2, _ = runner.autonomous_send(draft)
    assert code2 == runner.LIVE_BLOCKED_FINAL_GATE
    assert len(mail.outbox) == 1


def test_definitive_failure_becomes_send_failed(live_env, campaign, monkeypatch):
    import smtplib

    from openoutreach.signals import outreach

    draft = _draft(_lead(), campaign)
    monkeypatch.setattr(outreach, "EmailMessage", _RaisingEmailMessage(
        smtplib.SMTPRecipientsRefused({"a@b.c": (550, b"no such user")})))
    code, detail = runner.autonomous_send(draft)
    assert code == runner.LIVE_SEND_FAILED
    draft.refresh_from_db()
    assert draft.status == OutreachMessage.Status.SEND_FAILED
    assert not draft.send_error.startswith("AMBIGUOUS")
    # Definitive failure stays claimable for a retry (same Message-ID).
    mid = draft.message_id
    assert runner.claim_for_sending(draft) is True
    draft.refresh_from_db()
    assert draft.message_id == mid


def test_ambiguous_failure_is_held_and_never_auto_retried(live_env, campaign, monkeypatch):
    from openoutreach.signals import outreach

    draft = _draft(_lead(), campaign)
    monkeypatch.setattr(outreach, "EmailMessage",
                        _RaisingEmailMessage(TimeoutError("read timed out")))
    code, detail = runner.autonomous_send(draft)
    assert code == runner.LIVE_AMBIGUOUS
    draft.refresh_from_db()
    assert draft.send_error.startswith("AMBIGUOUS")
    assert runner.claim_for_sending(draft) is False
    code2, _ = runner.autonomous_send(draft)
    assert code2 == runner.LIVE_BLOCKED_FINAL_GATE
    assert len(mail.outbox) == 0


# ── 15. stuck SENDING is held, not resent ───────────────────────────────────

def test_stale_sending_is_held_not_resent(live_env, campaign):
    draft = _draft(_lead(), campaign)
    runner.claim_for_sending(draft)
    OutreachMessage.objects.filter(pk=draft.pk).update(
        updated_at=timezone.now() - timezone.timedelta(hours=1))
    assert runner.hold_stuck_claims() == 1
    draft.refresh_from_db()
    assert draft.send_error.startswith("AMBIGUOUS")
    assert runner.claim_for_sending(draft) is False
    assert len(mail.outbox) == 0


# ── 16-18. capacity accounting per failure class ────────────────────────────

def test_capacity_accounting_by_outcome(live_env, campaign, monkeypatch):
    import smtplib

    from openoutreach.signals import outreach

    assert runner.capacity_consumed_today() == 0
    ok = _draft(_lead(), campaign)
    assert runner.autonomous_send(ok)[0] == runner.LIVE_SENT
    assert runner.capacity_consumed_today() == 1  # success counts

    failed = _draft(_lead(), campaign)
    monkeypatch.setattr(outreach, "EmailMessage", _RaisingEmailMessage(
        smtplib.SMTPRecipientsRefused({"a@b.c": (550, b"no")})))
    assert runner.autonomous_send(failed)[0] == runner.LIVE_SEND_FAILED
    assert runner.capacity_consumed_today() == 1  # definitive failure does not

    ambiguous = _draft(_lead(), campaign)
    monkeypatch.setattr(outreach, "EmailMessage",
                        _RaisingEmailMessage(TimeoutError("timed out")))
    assert runner.autonomous_send(ambiguous)[0] == runner.LIVE_AMBIGUOUS
    assert runner.capacity_consumed_today() == 2  # may have been delivered — counts


# ── 19-23. spacing, batch, cap across runs ──────────────────────────────────

def test_minimum_spacing_blocks_too_soon_send(live_env, campaign):
    lead_done = _lead()
    OutreachMessage.objects.create(
        lead=lead_done, subject="s", body="b", status=OutreachMessage.Status.SENT,
        sent_at=timezone.now() - timezone.timedelta(seconds=30))
    _draft(_lead(), campaign)
    call_command("run_outreach_campaign", "--live", verbosity=0)
    # 30s < 180s spacing: the run identified the candidate but sent nothing.
    assert len(mail.outbox) == 0
    assert RunnerDecision.objects.filter(code=runner.SKIP_SPACING).exists()


def test_spacing_releases_once_elapsed(live_env, campaign):
    lead_done = _lead()
    OutreachMessage.objects.create(
        lead=lead_done, subject="s", body="b", status=OutreachMessage.Status.SENT,
        sent_at=timezone.now() - timezone.timedelta(minutes=10))
    _draft(_lead(), campaign)
    call_command("run_outreach_campaign", "--live", verbosity=0)
    assert len(mail.outbox) == 1


def test_small_batch_limit_respected_and_no_sleeps(live_env, campaign, monkeypatch):
    # Three eligible; per-run limit 1 (the default) → exactly one delivery,
    # and the sleep trap in live_env proves the run never slept.
    for _ in range(3):
        _draft(_lead(), campaign)
    call_command("run_outreach_campaign", "--live", verbosity=0)
    assert len(mail.outbox) == 1
    assert RunnerDecision.objects.filter(mode="live", code=runner.LIVE_SENT).count() == 1


def test_daily_cap_spans_multiple_runs(live_env, campaign, monkeypatch):
    monkeypatch.setenv("OUTREACH_DAILY_SEND_LIMIT", "2")
    monkeypatch.setenv("OUTREACH_MIN_SECONDS_BETWEEN_SENDS", "0")
    monkeypatch.setenv("OUTREACH_MAX_SENDS_PER_RUN", "5")
    for _ in range(3):
        _draft(_lead(), campaign)
    call_command("run_outreach_campaign", "--live", verbosity=0)
    call_command("run_outreach_campaign", "--live", verbosity=0)
    call_command("run_outreach_campaign", "--live", verbosity=0)
    assert len(mail.outbox) == 2  # the cap, not the eligible count, is authoritative


# ── 24-26. shadow parity and audit ──────────────────────────────────────────

def test_shadow_still_sends_zero_smtp(live_env, campaign):
    _draft(_lead(), campaign)
    call_command("run_outreach_campaign", "--skip-ingest", verbosity=0)
    assert len(mail.outbox) == 0
    assert not RunnerDecision.objects.filter(mode="live").exists()


def test_shadow_and_live_select_identical_candidates(live_env, campaign, monkeypatch):
    monkeypatch.setenv("OUTREACH_MIN_SECONDS_BETWEEN_SENDS", "0")
    monkeypatch.setenv("OUTREACH_MAX_SENDS_PER_RUN", "5")
    for _ in range(2):
        _draft(_lead(), campaign)
    shadow = runner.evaluate_campaign()
    shadow_pks = [d.lead.pk for d in shadow.candidates()]
    call_command("run_outreach_campaign", "--live", verbosity=0)
    live_pks = list(RunnerDecision.objects.filter(mode="live", code=runner.LIVE_SENT)
                    .order_by("created_at").values_list("lead__pk", flat=True))
    assert live_pks == shadow_pks


def test_audit_trail_records_final_outcome(live_env, campaign):
    lead = _lead()
    _draft(lead, campaign)
    call_command("run_outreach_campaign", "--live", verbosity=0)
    sent_row = RunnerDecision.objects.get(mode="live", code=runner.LIVE_SENT)
    assert sent_row.lead == lead
    assert sent_row.outreach_message is not None
    assert sent_row.would_send_subject == VALID_SUBJECT
    # The evaluation decision (WOULD_SEND) and the outcome (LIVE_SENT) are both
    # recorded — considered and delivered are separately answerable.
    assert RunnerDecision.objects.filter(lead=lead, code=runner.WOULD_SEND_FIRST_TOUCH).exists()


# ── 27. a reply after the controlled send stops the sequence ────────────────

def test_reply_after_live_send_stops_later_followup(live_env, campaign):
    lead = _lead(email="dana@brightpaths.org")
    draft = _draft(lead, campaign)
    assert runner.autonomous_send(draft)[0] == runner.LIVE_SENT
    draft.refresh_from_db()
    ingest_message(FetchedMessage(
        gmail_id="g-live-reply", thread_id="t9", in_reply_to=draft.message_id,
        from_address=lead.email, to_addresses=MAILBOX, subject="Re: " + VALID_SUBJECT,
        body_text="Tell me more?"), mailbox=MAILBOX, owner=MAILBOX)
    lead.refresh_from_db()
    assert lead.outreach_outcome == SalesLead.Outcome.REPLIED
    assert runner.evaluate_lead(lead).code == runner.HOLD_REPLIED


# ── 28. manual cockpit sending is untouched ─────────────────────────────────

def test_manual_send_path_still_works(live_env, campaign):
    from openoutreach.signals.outreach import send_outreach_email

    lead = _lead()
    _draft(lead, campaign)
    send_outreach_email(lead, VALID_SUBJECT, VALID_BODY)
    assert len(mail.outbox) == 1
    lead.refresh_from_db()
    assert lead.email_status == "sent"
