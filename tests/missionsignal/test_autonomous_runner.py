"""Gap 4A: the autonomous runner, shadow mode — decisions without deliveries.

The invariants:

* the runner enforces the operating order itself: ingest → freshness → gates →
  eligibility → validation → pacing. Stale or failed inbound visibility yields
  zero send candidates, never a warning-and-continue;
* every lead gets one explicit decision — nothing is inferred from "no error";
* follow-up timing counts from the last SENT touch's sent_at only;
* shadow mode delivers nothing and mutates nothing that implies a send;
* live mode refuses, unconditionally, in this build;
* the atomic SENDING claim admits exactly one worker and never an AMBIGUOUS row.
"""
from __future__ import annotations

import pytest
from django.core import mail
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from openoutreach.signals import runner
from openoutreach.signals.ingest import ingest_mailbox, ingest_message, FetchedMessage
from openoutreach.signals.models import (
    EmailOptOut,
    MailboxCursor,
    OutreachAngle,
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
def fresh_mailbox(monkeypatch):
    monkeypatch.setenv("OUTREACH_REPLY_MAILBOX", MAILBOX)
    monkeypatch.setenv("OUTREACH_BOUNCE_MAILBOX", MAILBOX)
    MailboxCursor.objects.create(mailbox=MAILBOX, last_success_at=timezone.now())


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


def _sent(lead, days_ago=20, position=1, angle=OutreachAngle.COUNTY_FUNDING, **kw):
    return OutreachMessage.objects.create(**{
        "lead": lead, "subject": "opener", "body": "first touch",
        "status": OutreachMessage.Status.SENT,
        "sent_at": timezone.now() - timezone.timedelta(days=days_ago),
        "sequence_position": position, "primary_angle": angle,
        "message_id": f"<t{lead.pk}-{position}@anansiatlas.com>",
        **kw,
    })


def _draft(lead, campaign=None, subject=VALID_SUBJECT, body=VALID_BODY, position=1, **kw):
    return OutreachMessage.objects.create(**{
        "lead": lead, "campaign": campaign, "subject": subject, "body": body,
        "status": OutreachMessage.Status.DRAFTED, "sequence_position": position,
        "personalization": OutreachMessage.Personalization.CATEGORY_RELEVANT,
        **kw,
    })


def _codes(result):
    return {d.lead.pk: d.code for d in result.decisions if d.lead is not None}


# ── 1-3. the runner enforces freshness itself ───────────────────────────────

def test_fresh_mailboxes_allow_evaluation(fresh_mailbox, campaign):
    lead = _lead()
    _draft(lead, campaign)
    result = runner.evaluate_campaign()
    assert result.freshness_hold == ""
    assert _codes(result)[lead.pk] == runner.WOULD_SEND_FIRST_TOUCH


def test_stale_mailbox_yields_zero_candidates(monkeypatch, campaign):
    monkeypatch.setenv("OUTREACH_REPLY_MAILBOX", MAILBOX)
    monkeypatch.setenv("OUTREACH_BOUNCE_MAILBOX", MAILBOX)
    MailboxCursor.objects.create(
        mailbox=MAILBOX,
        last_success_at=timezone.now() - timezone.timedelta(hours=6))
    lead = _lead()
    _draft(lead, campaign)
    result = runner.evaluate_campaign()
    assert result.candidates() == []
    assert [d.code for d in result.decisions] == [runner.HOLD_MAILBOX_STALE]


def test_ingestion_failure_yields_zero_candidates(fresh_mailbox, campaign):
    lead = _lead()
    _draft(lead, campaign)

    class FailingTransport:
        def fetch_new(self, history_id):
            raise ConnectionError("gmail down")

    ingest_mailbox(FailingTransport(), mailbox=MAILBOX, owner=MAILBOX)
    result = runner.evaluate_campaign()
    assert result.candidates() == []
    assert result.decisions[0].code == runner.HOLD_MAILBOX_STALE


# ── 4-6. sequence eligibility from actual message history ───────────────────

def test_eligible_untouched_lead_is_first_touch_candidate(fresh_mailbox, campaign):
    lead = _lead()
    draft = _draft(lead, campaign)
    d = runner.evaluate_lead(lead)
    assert d.code == runner.WOULD_SEND_FIRST_TOUCH
    assert d.message == draft  # 16. the existing valid draft is reused


def test_opener_before_wait_period_is_not_due(fresh_mailbox, campaign):
    lead = _lead()
    _sent(lead, days_ago=3)
    _draft(lead, campaign, position=2)
    assert runner.evaluate_lead(lead).code == runner.SKIP_NOT_DUE


def test_opener_after_wait_period_becomes_followup_candidate(fresh_mailbox, campaign):
    lead = _lead()
    _sent(lead, days_ago=20)
    _draft(lead, campaign, position=2)
    d = runner.evaluate_lead(lead)
    assert d.code == runner.WOULD_SEND_FOLLOWUP


def test_followup_clock_counts_from_sent_at_not_draft_or_failure(fresh_mailbox, campaign):
    # A failed send 20 days ago and a fresh draft must NOT make a follow-up due:
    # nothing was ever delivered, so this is still a first touch.
    lead = _lead()
    OutreachMessage.objects.create(
        lead=lead, subject="s", body="b", status=OutreachMessage.Status.SEND_FAILED,
        send_error="SMTPRecipientsRefused: boom",
        created_at=timezone.now() - timezone.timedelta(days=20))
    _draft(lead, campaign)
    d = runner.evaluate_lead(lead)
    assert d.code == runner.WOULD_SEND_FIRST_TOUCH


def test_manual_next_follow_up_is_a_brake_never_an_accelerator(fresh_mailbox, campaign):
    lead = _lead(next_follow_up=(timezone.localdate() + timezone.timedelta(days=30)))
    _sent(lead, days_ago=20)
    _draft(lead, campaign, position=2)
    assert runner.evaluate_lead(lead).code == runner.SKIP_NOT_DUE
    # A past manual date does not make an un-due follow-up due.
    lead2 = _lead(next_follow_up=(timezone.localdate() - timezone.timedelta(days=5)))
    _sent(lead2, days_ago=2)
    _draft(lead2, campaign, position=2)
    assert runner.evaluate_lead(lead2).code == runner.SKIP_NOT_DUE


# ── 7-14. holds and terminals ───────────────────────────────────────────────

@pytest.mark.parametrize("outcome", [SalesLead.Outcome.REPLIED, SalesLead.Outcome.INTERESTED])
def test_open_conversation_holds(fresh_mailbox, campaign, outcome):
    lead = _lead(outreach_outcome=outcome)
    _sent(lead, days_ago=20)
    _draft(lead, campaign, position=2)
    assert runner.evaluate_lead(lead).code == runner.HOLD_REPLIED


@pytest.mark.parametrize("outcome", [SalesLead.Outcome.NOT_INTERESTED,
                                     SalesLead.Outcome.BOUNCED,
                                     SalesLead.Outcome.MEETING])
def test_terminal_outcomes_skip(fresh_mailbox, campaign, outcome):
    lead = _lead(outreach_outcome=outcome)
    _draft(lead, campaign)
    assert runner.evaluate_lead(lead).code == runner.SKIP_TERMINAL


def test_closed_won_is_terminal(fresh_mailbox, campaign):
    lead = _lead(status=SalesLead.Status.CLOSED)
    _draft(lead, campaign)
    assert runner.evaluate_lead(lead).code == runner.SKIP_TERMINAL


def test_opted_out_lead_cannot_become_candidate(fresh_mailbox, campaign):
    lead = _lead()
    EmailOptOut.objects.create(email=lead.email)
    _draft(lead, campaign)
    assert runner.evaluate_lead(lead).code == runner.SKIP_OPTED_OUT


def test_review_and_disqualified_cannot_become_candidates(fresh_mailbox, campaign):
    held = _lead(disposition=SalesLead.DISPOSITION_REVIEW)
    out = _lead(disposition=SalesLead.DISPOSITION_DISQUALIFIED)
    _draft(held, campaign)
    _draft(out, campaign)
    assert runner.evaluate_lead(held).code == runner.HOLD_REVIEW
    assert runner.evaluate_lead(out).code == runner.HOLD_DISQUALIFIED


# ── 15, 21, 22. ambiguity and the atomic claim ──────────────────────────────

def test_ambiguous_previous_send_holds_and_cannot_be_claimed(fresh_mailbox, campaign):
    lead = _lead()
    ambiguous = OutreachMessage.objects.create(
        lead=lead, subject="s", body="b", status=OutreachMessage.Status.SEND_FAILED,
        send_error="AMBIGUOUS — the server may have accepted this...")
    assert runner.evaluate_lead(lead).code == runner.HOLD_AMBIGUOUS_SEND
    assert runner.claim_for_sending(ambiguous) is False


def test_two_workers_cannot_claim_the_same_message(fresh_mailbox, campaign):
    lead = _lead()
    draft = _draft(lead, campaign)
    assert runner.claim_for_sending(draft) is True
    assert runner.claim_for_sending(draft) is False  # the race's loser
    draft.refresh_from_db()
    assert draft.status == OutreachMessage.Status.SENDING


def test_stuck_sending_claim_follows_the_ambiguous_hold_policy(fresh_mailbox, campaign):
    lead = _lead()
    draft = _draft(lead, campaign)
    runner.claim_for_sending(draft)
    OutreachMessage.objects.filter(pk=draft.pk).update(
        updated_at=timezone.now() - timezone.timedelta(hours=2))
    # A recent stuck claim is reported, not touched.
    assert runner.evaluate_lead(lead).code == runner.HOLD_AMBIGUOUS_SEND
    held = runner.hold_stuck_claims()
    assert held == 1
    draft.refresh_from_db()
    assert draft.status == OutreachMessage.Status.SEND_FAILED
    assert draft.send_error.startswith("AMBIGUOUS")
    # And the recovery result stays unclaimable — no auto-retry of ambiguity.
    assert runner.claim_for_sending(draft) is False
    # Message-ID (if minted) would live on the row — recovery touched status only.


# ── 16-18. draft reuse, absence, staleness ──────────────────────────────────

def test_missing_draft_is_flagged_not_generated(fresh_mailbox, campaign):
    lead = _lead()
    d = runner.evaluate_lead(lead)
    assert d.code == runner.NEEDS_DRAFT
    # Policy: the runner never generates drafts — drafting stays in the one
    # human-reviewed path (preview_cohort_drafts).
    assert OutreachMessage.objects.filter(lead=lead).count() == 0


def test_stale_draft_predating_last_sent_touch_is_rejected(fresh_mailbox, campaign):
    lead = _lead()
    draft = _draft(lead, campaign, position=2)
    OutreachMessage.objects.filter(pk=draft.pk).update(
        created_at=timezone.now() - timezone.timedelta(days=40))
    _sent(lead, days_ago=20)
    d = runner.evaluate_lead(lead)
    assert d.code == runner.NEEDS_DRAFT
    assert "predates" in d.reason


def test_draft_predating_inbound_mail_is_rejected(fresh_mailbox, campaign):
    lead = _lead(email="dana@brightpaths.org")
    _sent(lead, days_ago=20, angle=OutreachAngle.COUNTY_FUNDING)
    _draft(lead, campaign, position=2)
    # An autoresponder arrives after the draft — no outcome change (OOO is
    # neutral), but the context changed and the draft may not auto-send.
    ingest_message(FetchedMessage(
        gmail_id="g-ooo", thread_id="t1", in_reply_to=f"<t{lead.pk}-1@anansiatlas.com>",
        from_address=lead.email, to_addresses=MAILBOX, subject="Automatic reply: away",
        body_text="Out of office.", headers={"Auto-Submitted": "auto-replied"}),
        mailbox=MAILBOX, owner=MAILBOX)
    d = runner.evaluate_lead(lead)
    assert d.code == runner.NEEDS_DRAFT
    assert "inbound" in d.reason


# ── 19-20. pacing and priority ──────────────────────────────────────────────

def test_daily_cap_limits_candidates(fresh_mailbox, campaign, monkeypatch):
    monkeypatch.setenv("OUTREACH_DAILY_SEND_LIMIT", "2")
    for _ in range(3):
        _draft(_lead(), campaign)
    result = runner.evaluate_campaign()
    codes = [d.code for d in result.decisions]
    assert codes.count(runner.WOULD_SEND_FIRST_TOUCH) == 2
    assert codes.count(runner.SKIP_CAP_REACHED) == 1


def test_sends_today_consume_capacity(fresh_mailbox, campaign, monkeypatch):
    monkeypatch.setenv("OUTREACH_DAILY_SEND_LIMIT", "2")
    spent = _lead()
    OutreachMessage.objects.create(
        lead=spent, subject="s", body="b", status=OutreachMessage.Status.SENT,
        sent_at=timezone.now())
    for _ in range(2):
        _draft(_lead(), campaign)
    result = runner.evaluate_campaign()
    codes = [d.code for d in result.decisions]
    assert codes.count(runner.WOULD_SEND_FIRST_TOUCH) == 1
    assert codes.count(runner.SKIP_CAP_REACHED) == 1


def test_priority_is_stable_followups_before_first_touches(fresh_mailbox, campaign):
    first = _lead()
    _draft(first, campaign)
    follow = _lead()
    _sent(follow, days_ago=20)
    _draft(follow, campaign, position=2)
    result = runner.evaluate_campaign()
    candidates = result.candidates()
    assert [d.lead.pk for d in candidates] == [follow.pk, first.pk]
    # Deterministic across runs — no queryset nondeterminism choosing orgs.
    again = runner.evaluate_campaign()
    assert [d.lead.pk for d in again.candidates()] == [d.lead.pk for d in candidates]


# ── 25-28. deterministic validation ─────────────────────────────────────────

def test_dead_cta_blocks_the_draft(fresh_mailbox, campaign):
    lead = _lead()
    _draft(lead, campaign, body="Book 30 minutes with me to walk through it.")
    d = runner.evaluate_lead(lead)
    assert d.code == runner.INVALID_DRAFT
    assert "link" in d.reason


def test_overlong_subject_blocks_the_draft(fresh_mailbox, campaign):
    lead = _lead()
    _draft(lead, campaign,
           subject="County funding for youth work across all five central Florida counties")
    assert runner.evaluate_lead(lead).code == runner.INVALID_DRAFT


def test_first_touch_price_rule_is_enforced_deterministically(fresh_mailbox, campaign):
    lead = _lead()
    _draft(lead, campaign,
           body=VALID_BODY + "\nFounding partners lock in at $150/month.")
    d = runner.evaluate_lead(lead)
    assert d.code == runner.INVALID_DRAFT
    assert "price" in d.reason
    # Later in the sequence the price is allowed — the rule is first-touch only.
    lead2 = _lead()
    _sent(lead2, days_ago=20)
    _draft(lead2, campaign, position=2,
           body=VALID_BODY + "\nFounding partners lock in at $150/month.")
    assert runner.evaluate_lead(lead2).code == runner.WOULD_SEND_FOLLOWUP


def test_grant_dollar_figures_are_not_mistaken_for_price(fresh_mailbox, campaign):
    lead = _lead()
    _draft(lead, campaign,
           body=VALID_BODY + "\nThe county released $250,000 for youth services.")
    assert runner.evaluate_lead(lead).code == runner.WOULD_SEND_FIRST_TOUCH


def test_missing_booking_link_configuration_fails_closed(fresh_mailbox):
    # No campaign with a booking link exists at all — the CTA cannot be
    # validated, so autonomy may not vouch for the draft.
    lead = _lead()
    _draft(lead, campaign=None)
    d = runner.evaluate_lead(lead)
    assert d.code == runner.INVALID_DRAFT
    assert "booking link" in d.reason


def test_category_relevant_leads_remain_eligible(fresh_mailbox, campaign):
    lead = _lead()
    _draft(lead, campaign)  # personalization=category_relevant in the factory
    assert runner.evaluate_lead(lead).code == runner.WOULD_SEND_FIRST_TOUCH


def test_missing_research_holds_rather_than_drafting_blind(fresh_mailbox, campaign):
    lead = _lead(research_profile="", notes="old mixed notes with stranded research")
    assert runner.evaluate_lead(lead).code == runner.HOLD_RESEARCH


# ── 23. the sequence ends at max touches ────────────────────────────────────

def test_max_touch_limit_ends_the_sequence(fresh_mailbox, campaign, monkeypatch):
    lead = _lead()
    _sent(lead, days_ago=40, position=1)
    _sent(lead, days_ago=20, position=2)
    _draft(lead, campaign, position=3)  # a third draft must not revive it
    d = runner.evaluate_lead(lead)
    assert d.code == runner.SKIP_ALREADY_SENT
    # Raising the configured ceiling is the only thing that reopens it.
    monkeypatch.setenv("OUTREACH_MAX_TOUCHES", "3")
    assert runner.evaluate_lead(lead).code == runner.WOULD_SEND_FOLLOWUP


# ── legacy history: automation refuses to guess what it never recorded ──────

def test_legacy_sent_lead_without_message_rows_holds(fresh_mailbox, campaign):
    # The original 13 leads were emailed before OutreachMessage existed.
    lead = _lead(email_status="sent")
    _draft(lead, campaign, position=2)
    d = runner.evaluate_lead(lead)
    assert d.code == runner.HOLD_LEGACY_HISTORY


def test_sent_row_without_sent_at_holds_instead_of_crashing(fresh_mailbox, campaign):
    lead = _lead()
    OutreachMessage.objects.create(
        lead=lead, subject="s", body="b", status=OutreachMessage.Status.SENT,
        sent_at=None)  # legacy mark-sent row
    _draft(lead, campaign, position=2)
    d = runner.evaluate_lead(lead)
    assert d.code == runner.HOLD_LEGACY_HISTORY


# ── 27. the follow-up's angle context comes from the SENT record ────────────

def test_followup_angle_lookup_uses_the_sent_touch(fresh_mailbox, campaign):
    lead = _lead()
    _sent(lead, days_ago=20, angle=OutreachAngle.COUNTY_FUNDING)
    _draft(lead, campaign, position=2)  # a draft must never shadow the sent record
    prev = OutreachMessage.last_for(lead, sent_only=True)
    assert prev.primary_angle == OutreachAngle.COUNTY_FUNDING
    assert prev.status == OutreachMessage.Status.SENT


# ── 29. reply ingested immediately before evaluation prevents follow-up ─────

def test_reply_ingested_just_before_evaluation_prevents_followup(fresh_mailbox, campaign):
    lead = _lead(email="dana@brightpaths.org")
    _sent(lead, days_ago=20)
    _draft(lead, campaign, position=2)
    assert runner.evaluate_lead(lead).code == runner.WOULD_SEND_FOLLOWUP
    ingest_message(FetchedMessage(
        gmail_id="g-reply", thread_id="t1", in_reply_to=f"<t{lead.pk}-1@anansiatlas.com>",
        from_address=lead.email, to_addresses=MAILBOX, subject="Re: opener",
        body_text="Interesting — tell me more?"), mailbox=MAILBOX, owner=MAILBOX)
    lead.refresh_from_db()
    assert runner.evaluate_lead(lead).code == runner.HOLD_REPLIED


# ── 23-24 and the command: shadow delivers nothing, mutates nothing ─────────

def test_shadow_command_sends_zero_smtp_and_mutates_nothing(fresh_mailbox, campaign):
    lead = _lead()
    draft = _draft(lead, campaign)
    before = (lead.email_status, lead.outreach_outcome, lead.status)
    call_command("run_outreach_campaign", "--skip-ingest", verbosity=0)
    assert len(mail.outbox) == 0
    lead.refresh_from_db()
    draft.refresh_from_db()
    assert (lead.email_status, lead.outreach_outcome, lead.status) == before
    assert draft.status == OutreachMessage.Status.DRAFTED
    assert draft.sent_at is None
    # The decision was recorded — shadow's one and only write.
    d = RunnerDecision.objects.get(lead=lead)
    assert d.code == runner.WOULD_SEND_FIRST_TOUCH
    assert d.would_send_subject == VALID_SUBJECT
    assert d.mode == "shadow"


def test_shadow_run_records_system_hold_when_mailbox_stale(monkeypatch, campaign):
    monkeypatch.setenv("OUTREACH_REPLY_MAILBOX", MAILBOX)
    monkeypatch.setenv("OUTREACH_BOUNCE_MAILBOX", MAILBOX)
    _draft(_lead(), campaign)
    call_command("run_outreach_campaign", "--skip-ingest", verbosity=0)
    assert len(mail.outbox) == 0
    assert list(RunnerDecision.objects.values_list("code", flat=True)) == [
        runner.HOLD_MAILBOX_STALE]


def test_live_mode_refuses_unconditionally(fresh_mailbox, campaign, monkeypatch):
    with pytest.raises(CommandError, match="not enabled"):
        call_command("run_outreach_campaign", "--live")
    # Even the future feature flag does not open it in this build.
    monkeypatch.setenv("OUTREACH_AUTOSEND_ENABLED", "true")
    with pytest.raises(CommandError, match="not enabled"):
        call_command("run_outreach_campaign", "--live")
    assert len(mail.outbox) == 0
