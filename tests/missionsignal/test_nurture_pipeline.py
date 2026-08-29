"""The nurture sequence: pipeline hand-off, the four send gates, and loud failure.

Context for the gates: this cron ran daily for a month reporting success while
sending nothing (no EMAIL_* vars → ConnectionRefusedError, swallowed per signup,
exit 0). Behind it sat ~4,132 mostly bot-generated signups on a domain being
reputation-warmed. These tests pin the behaviour that makes both halves of that
impossible — the queue can't discharge itself, and a dead transport can't look
like a quiet day.
"""

from datetime import timedelta

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from openoutreach.signals import nurture as nurture_mod
from openoutreach.signals.models import EmailOptOut, InterestSignup, SalesLead
from openoutreach.signals.nurture import MAX_STEP, send_due_nurture_emails

pytestmark = pytest.mark.django_db


def _signup(email="alex@hopeworks.org", *, age_days=8, step=2, **kwargs):
    signup = InterestSignup.objects.create(
        name=kwargs.pop("name", "Alex Doe"),
        organization=kwargs.pop("organization", "Hope Works"),
        email=email,
        nurture_step=step,
        **kwargs,
    )
    InterestSignup.objects.filter(pk=signup.pk).update(
        created_at=timezone.now() - timedelta(days=age_days)
    )
    signup.refresh_from_db()
    return signup


# ---------------------------------------------------------------- pipeline

def test_completed_sequence_creates_inbound_nurturing_lead(mailoutbox):
    _signup()
    run = send_due_nurture_emails()
    assert run.sent == 1
    lead = SalesLead.objects.get(email="alex@hopeworks.org")
    assert lead.source == SalesLead.Source.INBOUND
    assert lead.status == SalesLead.Status.NURTURING

    # idempotent — running again doesn't duplicate
    send_due_nurture_emails()
    assert SalesLead.objects.filter(email="alex@hopeworks.org").count() == 1


# ------------------------------------------------------------------- gates

def test_opted_out_signup_is_suppressed_and_retired(mailoutbox):
    signup = _signup(email="gone@example.org")
    EmailOptOut.objects.create(email="gone@example.org")

    run = send_due_nurture_emails()

    assert run.sent == 0
    assert run.suppressed == 1
    assert mailoutbox == []
    signup.refresh_from_db()
    # Retired, so the row stops being re-examined every single day...
    assert signup.nurture_step == MAX_STEP
    # ...but retiring is not completing: no pipeline lead.
    assert not SalesLead.objects.filter(email="gone@example.org").exists()


def test_aged_out_signup_is_retired_unsent(mailoutbox):
    """The structural answer to a queue that sat still while sending was broken."""
    signup = _signup(email="ancient@example.org", age_days=60, step=0)

    run = send_due_nurture_emails()

    assert run.sent == 0
    assert run.suppressed == 1
    assert mailoutbox == []
    signup.refresh_from_db()
    assert signup.nurture_step == MAX_STEP
    assert not SalesLead.objects.filter(email="ancient@example.org").exists()


def test_daily_limit_caps_attempted_sends(mailoutbox, monkeypatch):
    monkeypatch.setenv("NURTURE_DAILY_LIMIT", "2")
    for i in range(5):
        _signup(email=f"lead{i}@hopeworks.org", age_days=2, step=0)

    run = send_due_nurture_emails()

    assert run.sent == 2
    assert run.capped == 3
    assert len(mailoutbox) == 2


def test_missing_mailing_address_refuses_to_send(monkeypatch, mailoutbox):
    from openoutreach.signals import outreach

    monkeypatch.setattr(outreach, "OUTREACH_MAILING_ADDRESS", "")
    _signup(email="due@hopeworks.org", age_days=2, step=0)

    with pytest.raises(RuntimeError, match="OUTREACH_MAILING_ADDRESS"):
        send_due_nurture_emails()
    assert mailoutbox == []


def test_nothing_due_does_not_trip_the_mailing_address_check(monkeypatch):
    """The refusal fires when a message would have gone out, not on every run."""
    from openoutreach.signals import outreach

    monkeypatch.setattr(outreach, "OUTREACH_MAILING_ADDRESS", "")
    _signup(email="notyet@hopeworks.org", age_days=0, step=0)

    run = send_due_nurture_emails()
    assert run.skipped == 1
    assert run.sent == 0


def test_message_carries_unsubscribe_footer_and_headers(mailoutbox):
    _signup(email="reachable@hopeworks.org", age_days=2, step=0)

    send_due_nurture_emails()

    message = mailoutbox[0]
    assert "/unsubscribe/" in message.body
    assert "List-Unsubscribe" in message.extra_headers
    assert "List-Unsubscribe-Post" in message.extra_headers
    # The HTML alternative still rides along.
    assert message.alternatives and message.alternatives[0][1] == "text/html"


# --------------------------------------------------------- loud failure

def _break_transport(monkeypatch):
    def _raise(signup, step):
        raise ConnectionRefusedError("[Errno 111] Connection refused")

    monkeypatch.setattr(nurture_mod, "_send_step", _raise)


def test_send_failure_is_counted_not_hidden_in_skipped(monkeypatch):
    """The exact bug: failures used to increment the same counter as 'not due'."""
    _break_transport(monkeypatch)
    signup = _signup(email="broken@hopeworks.org", age_days=2, step=0)

    run = send_due_nurture_emails()

    assert run.failed == 1
    assert run.sent == 0
    assert run.skipped == 0
    assert run.total_failure is True
    signup.refresh_from_db()
    assert signup.nurture_step == 0  # not advanced — nothing was delivered


def test_total_failure_exits_non_zero(monkeypatch):
    _break_transport(monkeypatch)
    _signup(email="broken@hopeworks.org", age_days=2, step=0)

    with pytest.raises(CommandError, match="Every nurture send failed"):
        call_command("send_nurture_emails")


def test_quiet_run_still_succeeds(monkeypatch):
    """No candidates is not a failure — the command must stay green."""
    _break_transport(monkeypatch)
    call_command("send_nurture_emails")  # no signups at all


def test_partial_failure_does_not_fail_the_command(monkeypatch, mailoutbox):
    real_send = nurture_mod._send_step
    calls = {"n": 0}

    def _flaky(signup, step):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ConnectionRefusedError("transient")
        return real_send(signup, step)

    monkeypatch.setattr(nurture_mod, "_send_step", _flaky)
    _signup(email="a@hopeworks.org", age_days=2, step=0)
    _signup(email="b@hopeworks.org", age_days=2, step=0)

    call_command("send_nurture_emails")  # must not raise
    assert len(mailoutbox) == 1


# ------------------------------------------------- retire_stale_signups

def test_retire_stale_signups_reports_without_writing():
    signup = _signup(email="queued@example.org", age_days=40, step=0)

    call_command("retire_stale_signups")

    signup.refresh_from_db()
    assert signup.nurture_step == 0


def test_retire_stale_signups_confirm_retires_and_creates_no_leads():
    stale = _signup(email="queued@example.org", age_days=40, step=0)
    fresh = _signup(email="today@example.org", age_days=0, step=0)

    call_command(
        "retire_stale_signups",
        "--before", (timezone.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
        "--confirm",
    )

    stale.refresh_from_db()
    fresh.refresh_from_db()
    assert stale.nurture_step == MAX_STEP
    assert fresh.nurture_step == 0
    assert not SalesLead.objects.exists()


def test_retired_queue_sends_nothing_when_mail_starts_working(mailoutbox):
    """The whole point of the drain-then-credential order."""
    for i in range(20):
        _signup(email=f"bot{i}@immenseignite.info", age_days=40, step=0)

    call_command("retire_stale_signups", "--confirm")
    run = send_due_nurture_emails()

    assert run.sent == 0
    assert mailoutbox == []
