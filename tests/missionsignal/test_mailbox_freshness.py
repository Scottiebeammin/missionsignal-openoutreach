"""Mailbox freshness — the fail-closed gate for future autonomous sending.

The invariant under test: autonomous outbound may proceed only when every
configured inbound mailbox has a recent SUCCESSFUL ingestion. Stale, failed,
or never-synced visibility holds sending; a hold is mailbox health, never
lead evidence. Tests assert the invariant (hold vs no hold), never exact
error prose. Runner-phase tests still owed when the runner exists: a reply
ingested immediately before the send pass prevents the follow-up, and an
ingestion failure yields zero automated deliveries end-to-end.
"""
from __future__ import annotations

import pytest
from django.utils import timezone

from openoutreach.signals.ingest import (
    DEFAULT_MAX_STALENESS_MINUTES,
    ingest_mailbox,
    mailbox_freshness_hold,
)
from openoutreach.signals.models import EmailOptOut, MailboxCursor, SalesLead

pytestmark = pytest.mark.django_db

REPLY_BOX = "marcus@anansiatlas.com"
BOUNCE_BOX = "mail@anansiatlas.com"


class FakeTransport:
    def __init__(self, messages=(), new_cursor="hist-2", fail=False):
        self.messages = list(messages)
        self.new_cursor = new_cursor
        self.fail = fail

    def fetch_new(self, history_id):
        if self.fail:
            raise ConnectionError("mailbox unreachable")
        return list(self.messages), self.new_cursor


@pytest.fixture
def one_mailbox(monkeypatch):
    monkeypatch.setenv("OUTREACH_REPLY_MAILBOX", REPLY_BOX)
    monkeypatch.setenv("OUTREACH_BOUNCE_MAILBOX", REPLY_BOX)


@pytest.fixture
def two_mailboxes(monkeypatch):
    monkeypatch.setenv("OUTREACH_REPLY_MAILBOX", REPLY_BOX)
    monkeypatch.setenv("OUTREACH_BOUNCE_MAILBOX", BOUNCE_BOX)


def _fresh(mailbox, minutes_ago=5, **kw):
    return MailboxCursor.objects.create(
        mailbox=mailbox,
        last_success_at=timezone.now() - timezone.timedelta(minutes=minutes_ago),
        last_run_at=timezone.now() - timezone.timedelta(minutes=minutes_ago),
        **kw,
    )


# ── 1-3. fresh allows, stale holds, never-synced holds ──────────────────────

def test_recent_successful_ingestion_allows_autonomous_evaluation(one_mailbox):
    _fresh(REPLY_BOX)
    assert mailbox_freshness_hold() == ""


def test_stale_mailbox_holds_autonomous_sending(one_mailbox):
    _fresh(REPLY_BOX, minutes_ago=DEFAULT_MAX_STALENESS_MINUTES + 1)
    assert mailbox_freshness_hold() != ""


def test_never_synced_mailbox_holds(one_mailbox):
    # Cursor row exists (a run started) but no success has ever completed.
    MailboxCursor.objects.create(mailbox=REPLY_BOX, last_run_at=timezone.now())
    assert mailbox_freshness_hold() != ""


def test_no_cursor_row_at_all_holds(one_mailbox):
    assert mailbox_freshness_hold() != ""


def test_unconfigured_mailboxes_hold(monkeypatch):
    monkeypatch.delenv("OUTREACH_REPLY_MAILBOX", raising=False)
    monkeypatch.delenv("OUTREACH_BOUNCE_MAILBOX", raising=False)
    assert mailbox_freshness_hold() != ""


# ── 4. a failed attempt never refreshes last-success ────────────────────────

def test_failed_ingestion_does_not_refresh_last_success(one_mailbox):
    cursor = _fresh(REPLY_BOX, minutes_ago=30)
    before = cursor.last_success_at
    ingest_mailbox(FakeTransport(fail=True), mailbox=REPLY_BOX, owner=REPLY_BOX)
    cursor.refresh_from_db()
    assert cursor.last_success_at == before
    assert cursor.last_error
    # The 16:00-success / 16:30-failure case: the failed attempt itself holds.
    assert mailbox_freshness_hold() != ""


def test_last_attempt_failure_holds_even_inside_the_window(one_mailbox):
    _fresh(REPLY_BOX, minutes_ago=10, last_error="auth failure")
    assert mailbox_freshness_hold() != ""


# ── 5-7. one mailbox, two mailboxes, deduplication ──────────────────────────

def test_single_configured_mailbox_is_sufficient(one_mailbox):
    _fresh(REPLY_BOX)
    assert mailbox_freshness_hold() == ""


def test_two_mailboxes_require_both_fresh(two_mailboxes):
    _fresh(REPLY_BOX)
    _fresh(BOUNCE_BOX, minutes_ago=DEFAULT_MAX_STALENESS_MINUTES + 1)
    assert mailbox_freshness_hold() != ""
    MailboxCursor.objects.filter(mailbox=BOUNCE_BOX).update(last_success_at=timezone.now())
    assert mailbox_freshness_hold() == ""


def test_alias_configuration_evaluates_one_mailbox(one_mailbox):
    # Both env vars point at one box; one fresh cursor must be enough — a
    # phantom second requirement would hold forever.
    _fresh(REPLY_BOX)
    assert mailbox_freshness_hold() == ""
    assert MailboxCursor.objects.count() == 1


# ── 10-11. a hold is system health, never lead evidence ─────────────────────

def test_hold_does_not_touch_leads_or_optouts(one_mailbox):
    lead = SalesLead.objects.create(
        name="Dana Reed", organization="Brightpaths", email="dana@brightpaths.org",
        list_segment=SalesLead.Segment.COLD_FLORIDA_CRM,
        outreach_outcome=SalesLead.Outcome.AWAITING)
    disposition_before = lead.disposition
    assert mailbox_freshness_hold() != ""  # never synced
    lead.refresh_from_db()
    assert lead.outreach_outcome == SalesLead.Outcome.AWAITING
    assert lead.disposition == disposition_before
    assert EmailOptOut.objects.count() == 0


# ── 12. manual sending is governed separately ───────────────────────────────

def test_manual_send_path_does_not_consult_freshness(one_mailbox, monkeypatch):
    # The cockpit send is a human act on a mailbox the human can read directly;
    # it must not silently inherit the autonomous gate. Pin that the manual
    # path has no dependency on mailbox freshness state.
    import inspect

    from openoutreach.signals import outreach

    source = inspect.getsource(outreach)
    assert "mailbox_freshness_hold" not in source


# ── 13. recovery releases the hold with no human step ───────────────────────

def test_successful_ingestion_releases_the_hold(one_mailbox):
    _fresh(REPLY_BOX, minutes_ago=DEFAULT_MAX_STALENESS_MINUTES + 60,
           last_error="ConnectionError: mailbox unreachable")
    assert mailbox_freshness_hold() != ""
    ingest_mailbox(FakeTransport(), mailbox=REPLY_BOX, owner=REPLY_BOX)
    assert mailbox_freshness_hold() == ""


# ── configuration of the window ─────────────────────────────────────────────

def test_staleness_window_is_configurable(one_mailbox, monkeypatch):
    _fresh(REPLY_BOX, minutes_ago=20)
    monkeypatch.setenv("OUTREACH_MAILBOX_MAX_STALENESS_MINUTES", "15")
    assert mailbox_freshness_hold() != ""
    monkeypatch.setenv("OUTREACH_MAILBOX_MAX_STALENESS_MINUTES", "30")
    assert mailbox_freshness_hold() == ""


def test_garbage_window_value_falls_back_to_default(one_mailbox, monkeypatch):
    _fresh(REPLY_BOX, minutes_ago=DEFAULT_MAX_STALENESS_MINUTES - 5)
    monkeypatch.setenv("OUTREACH_MAILBOX_MAX_STALENESS_MINUTES", "soon")
    assert mailbox_freshness_hold() == ""
