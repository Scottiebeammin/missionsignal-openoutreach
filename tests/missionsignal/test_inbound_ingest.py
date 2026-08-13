"""Gap 3B: inbound observation, correlation, and reply/bounce safety.

Everything runs against FakeTransport — the pipeline (signals/ingest.py) is
transport-agnostic by design, so no test needs Gmail. The invariants:

* a real human reply pauses cold automation FIRST; interpretation is later;
* correlation never guesses — wrong-nonprofit attachment is worse than none;
* ingestion is idempotent and read-only;
* a failed poll holds the cursor rather than skipping mail.
"""
from __future__ import annotations

import pytest
from django.utils import timezone

from openoutreach.signals.ingest import (
    FetchedMessage,
    correlate,
    ingest_mailbox,
    ingest_message,
)
from openoutreach.signals.models import (
    InboundMessage,
    MailboxCursor,
    OutreachAngle,
    OutreachMessage,
    SalesLead,
    upgrade_outcome,
)

pytestmark = pytest.mark.django_db

MAILBOX = "marcus@anansiatlas.com"
OWNER = "marcus@anansiatlas.com"


class FakeTransport:
    """Yields canned messages; records every method called so read-only-ness is provable."""

    def __init__(self, messages, new_cursor="hist-2", fail=False):
        self.messages = messages
        self.new_cursor = new_cursor
        self.fail = fail
        self.calls: list[str] = []

    def fetch_new(self, history_id):
        self.calls.append(f"fetch_new({history_id})")
        if self.fail:
            raise ConnectionError("mailbox unreachable")
        return list(self.messages), self.new_cursor


def _lead(**kw):
    return SalesLead.objects.create(**{
        "name": "Dana Reed", "organization": "Brightpaths", "email": "dana@brightpaths.org",
        "email_status": "sent", "list_segment": SalesLead.Segment.COLD_FLORIDA_CRM,
        "outreach_outcome": SalesLead.Outcome.AWAITING,
        **kw,
    })


def _sent_message(lead, mid="<abc123@anansiatlas.com>", **kw):
    return OutreachMessage.objects.create(**{
        "lead": lead, "subject": "opener", "body": "first touch",
        "status": OutreachMessage.Status.SENT, "sent_at": timezone.now(),
        "message_id": mid, "primary_angle": OutreachAngle.COUNTY_FUNDING,
        **kw,
    })


def _reply(mid="<abc123@anansiatlas.com>", **kw):
    return FetchedMessage(**{
        "gmail_id": kw.pop("gmail_id", "g1"),
        "thread_id": kw.pop("thread_id", "t1"),
        "rfc_message_id": kw.pop("rfc_message_id", "<reply1@gmail.com>"),
        "in_reply_to": kw.pop("in_reply_to", mid),
        "from_address": kw.pop("from_address", "Dana Reed <dana@brightpaths.org>"),
        "to_addresses": kw.pop("to_addresses", MAILBOX),
        "subject": kw.pop("subject", "Re: opener"),
        "body_text": kw.pop("body_text", "Thanks for reaching out — tell me more?"),
        **kw,
    })


# ── 1-4. correlation hierarchy ──────────────────────────────────────────────

def test_exact_in_reply_to_correlation():
    lead = _lead()
    om = _sent_message(lead)
    got_lead, got_om, how = correlate(_reply(), mailbox=MAILBOX)
    assert (got_lead, got_om) == (lead, om)
    assert how == InboundMessage.Correlation.IN_REPLY_TO


def test_references_correlation_when_in_reply_to_is_damaged():
    lead = _lead()
    om = _sent_message(lead)
    msg = _reply(in_reply_to="", references="<noise@x.com> <abc123@anansiatlas.com>")
    got_lead, got_om, how = correlate(msg, mailbox=MAILBOX)
    assert (got_lead, got_om) == (lead, om)
    assert how == InboundMessage.Correlation.REFERENCES


def test_provider_thread_correlation_via_a_prior_correlated_sibling():
    lead = _lead()
    _sent_message(lead)
    ingest_message(_reply(gmail_id="g1", thread_id="t9"), mailbox=MAILBOX, owner=OWNER)
    # Second mail in the same Gmail thread with all threading headers stripped.
    msg = _reply(gmail_id="g2", thread_id="t9", in_reply_to="", references="",
                 from_address="someone-else@brightpaths.org")
    _, _, how = correlate(msg, mailbox=MAILBOX)
    assert how == InboundMessage.Correlation.THREAD


def test_address_fallback_attributes_to_the_latest_recent_touch():
    lead = _lead()
    _sent_message(lead, mid="<old@anansiatlas.com>")
    latest = _sent_message(lead, mid="<new@anansiatlas.com>", sequence_position=2)
    msg = _reply(gmail_id="g3", thread_id="t3", in_reply_to="", references="")
    got_lead, got_om, how = correlate(msg, mailbox=MAILBOX)
    assert got_lead == lead
    assert got_om == latest
    assert how == InboundMessage.Correlation.ADDRESS_FALLBACK


def test_ambiguous_sender_is_held_not_guessed():
    # Two leads share the address (a duplicate import). Attaching to either would
    # be a guess — the message ingests unresolved instead.
    _lead()
    _lead(organization="Brightpaths II")
    msg = _reply(in_reply_to="", references="")
    got_lead, got_om, how = correlate(msg, mailbox=MAILBOX)
    assert got_lead is None and got_om is None
    assert how == InboundMessage.Correlation.UNRESOLVED


# ── 5. idempotency ──────────────────────────────────────────────────────────

def test_duplicate_gmail_event_ingests_once():
    lead = _lead()
    _sent_message(lead)
    ingest_message(_reply(), mailbox=MAILBOX, owner=OWNER)
    record, disposition = ingest_message(_reply(), mailbox=MAILBOX, owner=OWNER)
    assert disposition == "duplicate" and record is None
    assert InboundMessage.objects.count() == 1


def test_duplicate_ingest_does_not_duplicate_state_transitions():
    lead = _lead()
    _sent_message(lead)
    transport = FakeTransport([_reply()])
    ingest_mailbox(transport, mailbox=MAILBOX, owner=OWNER)
    lead.refresh_from_db()
    lead.outreach_outcome = SalesLead.Outcome.MEETING   # Marcus advanced it by hand
    lead.save()
    ingest_mailbox(FakeTransport([_reply()]), mailbox=MAILBOX, owner=OWNER)  # re-poll
    lead.refresh_from_db()
    assert lead.outreach_outcome == SalesLead.Outcome.MEETING  # not knocked back


# ── 6-9. human replies and safety ───────────────────────────────────────────

def test_correlated_reply_is_stored_with_full_identity():
    lead = _lead()
    om = _sent_message(lead)
    record, _ = ingest_message(_reply(), mailbox=MAILBOX, owner=OWNER)
    assert record.lead == lead
    assert record.outreach_message == om
    assert record.rfc_message_id == "<reply1@gmail.com>"
    assert record.gmail_id == "g1" and record.thread_id == "t1"


def test_human_reply_immediately_pauses_cold_followup():
    lead = _lead()
    _sent_message(lead)
    ingest_message(_reply(), mailbox=MAILBOX, owner=OWNER)
    lead.refresh_from_db()
    assert lead.outreach_outcome == SalesLead.Outcome.REPLIED
    assert lead.followup_hold() != ""       # automated follow-up drafting holds
    assert lead.cold_outreach_block() == ""  # a human may still send by hand


def test_unclassified_reply_still_pauses_and_escalates():
    # Stage B doesn't exist yet; its absence must not weaken Stage A.
    lead = _lead()
    _sent_message(lead)
    record, _ = ingest_message(_reply(body_text="?????"), mailbox=MAILBOX, owner=OWNER)
    assert record.classification == InboundMessage.Classification.HUMAN_REPLY_UNCLASSIFIED
    assert record.needs_attention is True
    lead.refresh_from_db()
    assert lead.outreach_outcome == SalesLead.Outcome.REPLIED


def test_reply_is_attributed_to_the_touch_that_earned_it():
    lead = _lead()
    _sent_message(lead, mid="<opener@anansiatlas.com>")
    followup = _sent_message(lead, mid="<fu@anansiatlas.com>",
                             genre=OutreachMessage.Genre.COLD_FOLLOWUP, sequence_position=2)
    record, _ = ingest_message(_reply(mid="<fu@anansiatlas.com>"), mailbox=MAILBOX, owner=OWNER)
    assert record.outreach_message == followup
    assert followup.responses.count() == 1


# ── 10. Marcus's own replies ────────────────────────────────────────────────

def test_marcus_manual_reply_is_mirrored_not_treated_as_campaign_mail():
    lead = _lead()
    _sent_message(lead)
    before = OutreachMessage.objects.count()
    msg = FetchedMessage(
        gmail_id="g-own", thread_id="t1",
        from_address=f"Marcus Scott <{OWNER}>", to_addresses=lead.email,
        subject="Re: opener", body_text="Happy to walk you through it Thursday.")
    record, _ = ingest_message(msg, mailbox=MAILBOX, owner=OWNER)
    assert record.direction == InboundMessage.Direction.OUTBOUND_HUMAN
    assert record.classification == InboundMessage.Classification.OUTBOUND_HUMAN
    assert record.needs_attention is False
    # Not a campaign touch: no OutreachMessage created, no sequence increment.
    assert OutreachMessage.objects.count() == before
    lead.refresh_from_db()
    assert lead.outreach_outcome == SalesLead.Outcome.AWAITING  # not a prospect reply


# ── 11-13. bounces ──────────────────────────────────────────────────────────

def _dsn(status_line="Status: 5.1.1", failed="dana@brightpaths.org", **kw):
    return FetchedMessage(**{
        "gmail_id": kw.pop("gmail_id", "g-dsn"),
        "from_address": "Mail Delivery Subsystem <mailer-daemon@googlemail.com>",
        "to_addresses": "mail@anansiatlas.com",
        "subject": "Delivery Status Notification (Failure)",
        "body_text": f"Final-Recipient: rfc822; {failed}\n{status_line}\n",
        "headers": {"Content-Type": 'multipart/report; report-type=delivery-status'},
        **kw,
    })


def test_hard_bounce_sets_bounced_and_the_terminal_gate_holds():
    lead = _lead()
    _sent_message(lead)
    record, _ = ingest_message(_dsn(), mailbox="mail@anansiatlas.com", owner=OWNER)
    assert record.classification == InboundMessage.Classification.BOUNCE_HARD
    assert record.lead == lead              # via the DSN's failed-recipient
    lead.refresh_from_db()
    assert lead.outreach_outcome == SalesLead.Outcome.BOUNCED
    assert "bounced" in lead.cold_outreach_block()


def test_soft_dsn_does_not_hard_bounce_the_lead():
    lead = _lead()
    _sent_message(lead)
    record, _ = ingest_message(_dsn(status_line="Status: 4.2.2", gmail_id="g-soft"),
                               mailbox="mail@anansiatlas.com", owner=OWNER)
    assert record.classification == InboundMessage.Classification.BOUNCE_SOFT
    lead.refresh_from_db()
    assert lead.outreach_outcome == SalesLead.Outcome.AWAITING  # unchanged


def test_unresolved_dsn_is_flagged_for_a_human_not_acted_on():
    lead = _lead()
    _sent_message(lead)
    record, _ = ingest_message(_dsn(status_line="something nonstandard", gmail_id="g-odd"),
                               mailbox="mail@anansiatlas.com", owner=OWNER)
    assert record.classification == InboundMessage.Classification.DSN_UNRESOLVED
    assert record.needs_attention is True
    lead.refresh_from_db()
    assert lead.outreach_outcome == SalesLead.Outcome.AWAITING


def test_bounce_never_creates_an_opt_out():
    from openoutreach.signals.models import EmailOptOut

    lead = _lead()
    _sent_message(lead)
    ingest_message(_dsn(), mailbox="mail@anansiatlas.com", owner=OWNER)
    assert not EmailOptOut.objects.filter(email=lead.email).exists()


# ── 14. autoresponders ──────────────────────────────────────────────────────

def test_ooo_is_stored_but_changes_nothing_and_pages_no_one():
    lead = _lead()
    _sent_message(lead)
    msg = _reply(subject="Automatic reply: opener",
                 body_text="I am out of the office until Monday.",
                 headers={"Auto-Submitted": "auto-replied"})
    record, _ = ingest_message(msg, mailbox=MAILBOX, owner=OWNER)
    assert record.classification == InboundMessage.Classification.AUTORESPONDER
    assert record.needs_attention is False
    lead.refresh_from_db()
    assert lead.outreach_outcome == SalesLead.Outcome.AWAITING  # not a reply, not terminal


# ── 15-16. removal requests ─────────────────────────────────────────────────

def test_removal_request_stops_automation_and_escalates_prominently():
    lead = _lead()
    _sent_message(lead)
    record, _ = ingest_message(_reply(body_text="Please remove me from your list."),
                               mailbox=MAILBOX, owner=OWNER)
    assert record.classification == InboundMessage.Classification.REMOVAL_REQUEST
    assert record.needs_attention is True
    lead.refresh_from_db()
    # REPLIED holds the sequence immediately; the opt-out itself is Marcus's
    # deliberate act (compliance decisions are not automated in this first pass).
    assert lead.outreach_outcome == SalesLead.Outcome.REPLIED
    assert lead.followup_hold() != ""


def test_removal_phrase_inside_a_long_reply_is_not_misread():
    lead = _lead()
    _sent_message(lead)
    long_body = ("Interesting — please don't remove me from consideration for the pilot. " * 10)
    record, _ = ingest_message(_reply(body_text=long_body), mailbox=MAILBOX, owner=OWNER)
    assert record.classification == InboundMessage.Classification.HUMAN_REPLY_UNCLASSIFIED


# ── 17. read-only ingestion ─────────────────────────────────────────────────

def test_ingestion_only_ever_fetches():
    lead = _lead()
    _sent_message(lead)
    transport = FakeTransport([_reply()])
    ingest_mailbox(transport, mailbox=MAILBOX, owner=OWNER)
    # The transport interface has no mutating operations to call — provably:
    assert all(c.startswith("fetch_new(") for c in transport.calls)
    from openoutreach.signals.gmail_transport import GmailTransport
    for forbidden in ("delete", "archive", "modify", "trash", "send", "mark_read", "label"):
        assert not any(forbidden in name for name in dir(GmailTransport) if not name.startswith("__"))


# ── 18-19. polling and cursor discipline ────────────────────────────────────

def test_polling_is_idempotent_across_runs():
    lead = _lead()
    _sent_message(lead)
    for _ in range(3):
        ingest_mailbox(FakeTransport([_reply()]), mailbox=MAILBOX, owner=OWNER)
    assert InboundMessage.objects.count() == 1


def test_clean_run_advances_the_cursor():
    ingest_mailbox(FakeTransport([], new_cursor="hist-7"), mailbox=MAILBOX, owner=OWNER)
    cursor = MailboxCursor.objects.get(mailbox=MAILBOX)
    assert cursor.history_id == "hist-7"
    assert cursor.last_success_at is not None
    assert cursor.last_error == ""


def test_fetch_failure_holds_the_cursor():
    MailboxCursor.objects.create(mailbox=MAILBOX, history_id="hist-1")
    stats = ingest_mailbox(FakeTransport([], fail=True), mailbox=MAILBOX, owner=OWNER)
    cursor = MailboxCursor.objects.get(mailbox=MAILBOX)
    assert cursor.history_id == "hist-1"     # not advanced past unread mail
    assert "ConnectionError" in cursor.last_error
    assert stats.errors == 1


def test_message_level_failure_holds_the_cursor_but_keeps_good_messages(mocker):
    lead = _lead()
    _sent_message(lead)
    good, bad = _reply(gmail_id="g-good"), _reply(gmail_id="g-bad")
    real = ingest_message
    def flaky(msg, **kw):
        if msg.gmail_id == "g-bad":
            raise RuntimeError("boom")
        return real(msg, **kw)
    mocker.patch("openoutreach.signals.ingest.ingest_message", side_effect=flaky)
    MailboxCursor.objects.create(mailbox=MAILBOX, history_id="hist-1")
    ingest_mailbox(FakeTransport([good, bad], new_cursor="hist-9"), mailbox=MAILBOX, owner=OWNER)
    cursor = MailboxCursor.objects.get(mailbox=MAILBOX)
    assert cursor.history_id == "hist-1"     # held — g-bad will be re-read
    assert InboundMessage.objects.filter(gmail_id="g-good").exists()


# ── 20-21. mailbox configurations ───────────────────────────────────────────

def test_two_mailbox_configuration_keeps_events_separate():
    lead = _lead()
    _sent_message(lead)
    ingest_mailbox(FakeTransport([_reply()]), mailbox="marcus@anansiatlas.com", owner=OWNER)
    ingest_mailbox(FakeTransport([_dsn()]), mailbox="mail@anansiatlas.com", owner=OWNER)
    assert MailboxCursor.objects.count() == 2
    assert InboundMessage.objects.filter(mailbox="marcus@anansiatlas.com").count() == 1
    assert InboundMessage.objects.filter(mailbox="mail@anansiatlas.com").count() == 1


def test_alias_configuration_deduplicates_cleanly(monkeypatch):
    # mail@ turns out to be an alias: both settings point at one mailbox, the
    # same Gmail message can only exist once, and configured_mailboxes yields it once.
    from openoutreach.signals import gmail_transport as gt

    monkeypatch.setenv("OUTREACH_REPLY_MAILBOX", "marcus@anansiatlas.com")
    monkeypatch.setenv("OUTREACH_BOUNCE_MAILBOX", "marcus@anansiatlas.com")
    assert gt.configured_mailboxes() == ["marcus@anansiatlas.com"]
    lead = _lead()
    _sent_message(lead)
    ingest_mailbox(FakeTransport([_reply()]), mailbox=MAILBOX, owner=OWNER)
    ingest_mailbox(FakeTransport([_reply()]), mailbox=MAILBOX, owner=OWNER)
    assert InboundMessage.objects.count() == 1


# ── scope: Marcus's unrelated mail is never ingested ────────────────────────

def test_unrelated_personal_mail_is_skipped_unseen():
    _lead()
    msg = FetchedMessage(
        gmail_id="g-personal", from_address="newsletter@somesaas.com",
        to_addresses=MAILBOX, subject="Your weekly digest", body_text="...")
    record, disposition = ingest_message(msg, mailbox=MAILBOX, owner=OWNER)
    assert disposition == "irrelevant" and record is None
    assert InboundMessage.objects.count() == 0


# ── the outcome ladder ──────────────────────────────────────────────────────

def test_awaiting_cannot_overwrite_a_reply():
    lead = _lead(outreach_outcome=SalesLead.Outcome.REPLIED)
    changed = upgrade_outcome(lead, SalesLead.Outcome.AWAITING)
    assert changed is False
    lead.refresh_from_db()
    assert lead.outreach_outcome == SalesLead.Outcome.REPLIED


def test_send_bookkeeping_does_not_downgrade_a_reply(client, settings):
    # The race from the brief: reply ingested, then a send writes AWAITING.
    settings.DEFAULT_FROM_EMAIL = "mail@anansiatlas.com"
    from openoutreach.signals.outreach import send_outreach_email

    lead = _lead(email_status="not_sent", outreach_outcome=SalesLead.Outcome.REPLIED)
    send_outreach_email(lead, "a human follow-on", "written by hand")
    lead.refresh_from_db()
    assert lead.outreach_outcome == SalesLead.Outcome.REPLIED  # not reset to awaiting


def test_terminal_states_are_not_downgraded_by_ingestion():
    lead = _lead(outreach_outcome=SalesLead.Outcome.MEETING)
    _sent_message(lead)
    ingest_message(_reply(), mailbox=MAILBOX, owner=OWNER)
    lead.refresh_from_db()
    assert lead.outreach_outcome == SalesLead.Outcome.MEETING  # replied ranks below
