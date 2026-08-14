"""The manual-vs-autonomous send race — at most one delivery per lead/touch.

The audit finding: the runner claims a draft as SENDING and talks to SMTP; a
cockpit send clicked in that window used to create a *second* OutreachMessage
with the same content, invisible to the SENT-only duplicate check, and both
could deliver. The invariant pinned here:

* an active SENDING claim on a lead REFUSES a manual send — zero SMTP, zero
  new rows;
* a stale SENDING claim (worker died) routes through the stuck-claim policy —
  held AMBIGUOUS, still refused, never silently resent over;
* the reverse direction (manual finishes first) is closed by state: a SENT row
  is unclaimable and the evaluator skips the lead;
* normal manual sends and normal autonomous claims are unaffected.
"""
from __future__ import annotations

import pytest
from django.core import mail
from django.utils import timezone

from openoutreach.signals import runner
from openoutreach.signals.models import MailboxCursor, OutreachMessage, SalesLead
from openoutreach.signals.outreach import send_outreach_email

pytestmark = pytest.mark.django_db

MAILBOX = "marcus@anansiatlas.com"


def _lead(**kw):
    n = SalesLead.objects.count()
    return SalesLead.objects.create(**{
        "name": f"Lead {n}", "organization": f"Org {n}", "email": f"lead{n}@example.org",
        "list_segment": SalesLead.Segment.COLD_FLORIDA_CRM,
        "research_profile": "Verified: runs county-funded youth programs.",
        **kw,
    })


def _draft(lead, subject="County funding for youth work", body="the body", **kw):
    return OutreachMessage.objects.create(**{
        "lead": lead, "subject": subject, "body": body,
        "status": OutreachMessage.Status.DRAFTED, **kw,
    })


# ── 1-3. active SENDING blocks the manual path completely ───────────────────

def test_active_sending_blocks_manual_send():
    lead = _lead()
    draft = _draft(lead)
    assert runner.claim_for_sending(draft) is True  # the runner owns it
    rows_before = OutreachMessage.objects.filter(lead=lead).count()
    with pytest.raises(ValueError, match="already in flight"):
        send_outreach_email(lead, "A different subject", "a different body")
    assert len(mail.outbox) == 0                       # zero SMTP
    assert OutreachMessage.objects.filter(lead=lead).count() == rows_before  # no second row
    draft.refresh_from_db()
    assert draft.status == OutreachMessage.Status.SENDING  # claim untouched


def test_active_sending_blocks_even_identical_content():
    lead = _lead()
    draft = _draft(lead)
    runner.claim_for_sending(draft)
    with pytest.raises(ValueError, match="already in flight"):
        send_outreach_email(lead, draft.subject, draft.body)
    assert len(mail.outbox) == 0


# ── 4-5. stale SENDING: refused AND routed to the ambiguous hold ────────────

def test_stale_sending_refuses_manual_send_and_becomes_held():
    lead = _lead()
    draft = _draft(lead)
    runner.claim_for_sending(draft)
    OutreachMessage.objects.filter(pk=draft.pk).update(
        updated_at=timezone.now() - timezone.timedelta(hours=2))
    with pytest.raises(ValueError, match="AMBIGUOUS"):
        send_outreach_email(lead, "s", "b")
    assert len(mail.outbox) == 0
    draft.refresh_from_db()
    # Routed through the standard stuck-claim policy — never back to DRAFTED,
    # never resent over the top.
    assert draft.status == OutreachMessage.Status.SEND_FAILED
    assert draft.send_error.startswith("AMBIGUOUS")
    assert runner.claim_for_sending(draft) is False  # still unclaimable automatically


# ── 6-7. both race directions end in at most one delivery path ──────────────

def test_autonomous_claim_then_manual_attempt_leaves_one_path():
    lead = _lead()
    draft = _draft(lead)
    runner.claim_for_sending(draft)
    with pytest.raises(ValueError):
        send_outreach_email(lead, draft.subject, draft.body)
    # The runner's claim remains the only live path.
    assert OutreachMessage.objects.filter(
        lead=lead, status=OutreachMessage.Status.SENDING).count() == 1
    assert len(mail.outbox) == 0


def test_manual_send_first_then_autonomous_cannot_send_again(monkeypatch):
    monkeypatch.setenv("OUTREACH_REPLY_MAILBOX", MAILBOX)
    monkeypatch.setenv("OUTREACH_BOUNCE_MAILBOX", MAILBOX)
    MailboxCursor.objects.create(mailbox=MAILBOX, last_success_at=timezone.now())
    lead = _lead()
    draft = _draft(lead)
    send_outreach_email(lead, draft.subject, draft.body)   # manual wins the race
    assert len(mail.outbox) == 1
    draft.refresh_from_db()
    assert draft.status == OutreachMessage.Status.SENT
    # The sent row is unclaimable and the evaluator no longer sees a candidate.
    assert runner.claim_for_sending(draft) is False
    d = runner.evaluate_lead(lead)
    assert d.code not in runner.CANDIDATE_CODES
    assert len(mail.outbox) == 1                            # still exactly one delivery


# ── 8-11. nothing else changed ──────────────────────────────────────────────

def test_normal_manual_send_still_works_without_sending_conflict():
    lead = _lead()
    _draft(lead)
    send_outreach_email(lead, "County funding for youth work", "the body")
    assert len(mail.outbox) == 1
    assert OutreachMessage.objects.filter(
        lead=lead, status=OutreachMessage.Status.SENT).count() == 1


def test_normal_autonomous_claim_still_works():
    lead = _lead()
    draft = _draft(lead)
    assert runner.claim_for_sending(draft) is True


def test_duplicate_sent_protection_still_works():
    lead = _lead()
    _draft(lead)
    send_outreach_email(lead, "County funding for youth work", "the body")
    with pytest.raises(ValueError, match="already sent"):
        send_outreach_email(lead, "County funding for youth work", "the body")
    assert len(mail.outbox) == 1


def test_ambiguous_rows_remain_automatically_unclaimable():
    lead = _lead()
    row = OutreachMessage.objects.create(
        lead=lead, subject="s", body="b", status=OutreachMessage.Status.SEND_FAILED,
        send_error="AMBIGUOUS — the server may have accepted this...")
    assert runner.claim_for_sending(row) is False
