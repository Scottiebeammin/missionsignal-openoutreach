"""The autonomous outreach runner — decision engine, SHADOW MODE first.

Gap 4A. This module decides exactly what the system WOULD send, when, and why —
and in this phase, nothing more. Live delivery stays disabled until shadow
decisions have been validated against what Marcus would have done himself.

The operating order, which nothing here may reorder:

    ingest inbound mail
    → verify mailbox freshness (fail closed — see ingest.mailbox_freshness_hold)
    → evaluate lead/campaign safety gates
    → determine first-touch/follow-up eligibility
    → validate the draft deterministically
    → apply pacing/daily-cap rules
    → atomically claim (LIVE only — shadow never claims)
    → SHADOW: record the decision · LIVE (future): send via send_outreach_email

Design rules this module enforces:

* **No second path.** Eligibility reuses ``cold_outreach_block``,
  ``followup_hold``, ``is_opted_out``, ``research_gap``; validation reuses
  ``subject_problems``/``cta_problems`` from the drafting command. The runner
  adds sequencing and pacing — it re-implements no safety rule, and drafting
  itself stays in ``preview_cohort_drafts`` (one prompt assembly path).
* **One explicit decision per lead.** Never "no error so far" — every lead the
  runner considers gets a code and a reason it can be audited by.
* **Follow-up timing counts from the last SENT touch's ``sent_at``** — never
  from draft creation, failed sends, or queue time. The manual
  ``SalesLead.next_follow_up`` date survives as an operator *hold-until*
  override only: a future date delays automation, but the field can never make
  a lead due earlier than the computed rule. One canonical clock, human brake.
* **Ambiguous sends freeze the lane.** A SEND_FAILED row whose error is marked
  AMBIGUOUS, or a SENDING claim that never finalized, holds the lead for a
  human — automation never retries a message that may already be in the inbox.
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field

from django.utils import timezone

logger = logging.getLogger(__name__)

# ── decision codes ───────────────────────────────────────────────────────────

WOULD_SEND_FIRST_TOUCH = "WOULD_SEND_FIRST_TOUCH"
WOULD_SEND_FOLLOWUP = "WOULD_SEND_FOLLOWUP"
HOLD_MAILBOX_STALE = "HOLD_MAILBOX_STALE"
HOLD_REPLIED = "HOLD_REPLIED"
HOLD_REVIEW = "HOLD_REVIEW"
HOLD_DISQUALIFIED = "HOLD_DISQUALIFIED"
HOLD_AMBIGUOUS_SEND = "HOLD_AMBIGUOUS_SEND"
HOLD_IN_CONVERSATION = "HOLD_IN_CONVERSATION"
HOLD_RESEARCH = "HOLD_RESEARCH"
#: The lead was emailed before OutreachMessage existed (email_status says sent,
#: no SENT row / no sent_at), so the follow-up clock has no anchor. Automation
#: refuses to guess timing; these stay hand-sent from the cockpit.
HOLD_LEGACY_HISTORY = "HOLD_LEGACY_HISTORY"
SKIP_ALREADY_SENT = "SKIP_ALREADY_SENT"
SKIP_TERMINAL = "SKIP_TERMINAL"
SKIP_CAP_REACHED = "SKIP_CAP_REACHED"
SKIP_NOT_DUE = "SKIP_NOT_DUE"
SKIP_NO_EMAIL = "SKIP_NO_EMAIL"
SKIP_OPTED_OUT = "SKIP_OPTED_OUT"
NEEDS_DRAFT = "NEEDS_DRAFT"
INVALID_DRAFT = "INVALID_DRAFT"

#: Live-execution outcomes (mode="live" RunnerDecision rows). Shadow never
#: emits these — they exist only past the point where a claim was attempted.
LIVE_SENT = "LIVE_SENT"
LIVE_SEND_FAILED = "LIVE_SEND_FAILED"
LIVE_AMBIGUOUS = "LIVE_AMBIGUOUS"
LIVE_BLOCKED_FINAL_GATE = "LIVE_BLOCKED_FINAL_GATE"
SKIP_SPACING = "SKIP_SPACING"
SKIP_BATCH_LIMIT = "SKIP_BATCH_LIMIT"

CANDIDATE_CODES = (WOULD_SEND_FIRST_TOUCH, WOULD_SEND_FOLLOWUP)


@dataclass
class Decision:
    """One explicit, auditable verdict: a code, a human-readable reason, and the
    rows it is about. ``lead is None`` marks a run-level (system) decision."""

    code: str
    reason: str = ""
    lead: object = None
    message: object = None
    #: sort key for follow-up priority — the sent_at of the touch being followed.
    last_sent_at: object = None


@dataclass
class RunResult:
    decisions: list = field(default_factory=list)
    freshness_hold: str = ""

    def counts(self) -> dict:
        out: dict[str, int] = {}
        for d in self.decisions:
            out[d.code] = out.get(d.code, 0) + 1
        return out

    def candidates(self) -> list:
        return [d for d in self.decisions if d.code in CANDIDATE_CODES]


# ── configuration (env-level, like the freshness window) ─────────────────────

#: Conservative: the size of one hand-reviewed manual batch. A cron invocation
#: must never be able to send the whole database.
DEFAULT_DAILY_SEND_LIMIT = 20
#: Sends spaced at least this far apart within a run — burst control, not volume
#: control (the daily cap is volume control).
DEFAULT_MIN_SECONDS_BETWEEN_SENDS = 180
#: The current campaign is an opener plus one follow-up. Raise deliberately,
#: not by accident of data.
DEFAULT_MAX_TOUCHES = 2
DEFAULT_FIRST_FOLLOWUP_DAYS = 14
DEFAULT_SECOND_FOLLOWUP_DAYS = 14
#: A SENDING claim older than this never finalized — its worker died. The
#: message's delivery state is unknown, which is exactly what AMBIGUOUS means.
STUCK_CLAIM_MINUTES = 30


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    try:
        return int(raw) if raw else default
    except ValueError:
        logger.warning("%s=%r is not an integer — using the default %s", name, raw, default)
        return default


def daily_send_limit() -> int:
    return _int_env("OUTREACH_DAILY_SEND_LIMIT", DEFAULT_DAILY_SEND_LIMIT)


def min_seconds_between_sends() -> int:
    return _int_env("OUTREACH_MIN_SECONDS_BETWEEN_SENDS", DEFAULT_MIN_SECONDS_BETWEEN_SENDS)


def max_touches() -> int:
    return _int_env("OUTREACH_MAX_TOUCHES", DEFAULT_MAX_TOUCHES)


def followup_wait_days(touches_sent: int) -> int:
    """Days to wait after the Nth sent touch before the next becomes due."""
    if touches_sent <= 1:
        return _int_env("OUTREACH_FIRST_FOLLOWUP_DAYS", DEFAULT_FIRST_FOLLOWUP_DAYS)
    return _int_env("OUTREACH_SECOND_FOLLOWUP_DAYS", DEFAULT_SECOND_FOLLOWUP_DAYS)


def autosend_enabled() -> bool:
    """Half of the live-mode double gate (the other half is the explicit
    ``--live`` flag — neither alone delivers anything). Missing = false =
    autonomous SMTP delivery impossible. Production keeps this unset until the
    controlled canary in docs/outreach-live-canary.md."""
    return os.getenv("OUTREACH_AUTOSEND_ENABLED", "").strip().lower() in ("1", "true", "yes")


# ── pacing ───────────────────────────────────────────────────────────────────

#: Sends per cron invocation, deliberately 1: MIN_SECONDS_BETWEEN_SENDS is
#: enforced from persisted state with no sleeps, so a second send in the same
#: seconds-long invocation could never satisfy a 180s gap anyway. Volume comes
#: from cron frequency (every 10–15 min → the 20/day cap is reached over a few
#: hours), never from a long-running process. Raise this only together with a
#: lower MIN_SECONDS.
DEFAULT_MAX_SENDS_PER_RUN = 1


def max_sends_per_run() -> int:
    return _int_env("OUTREACH_MAX_SENDS_PER_RUN", DEFAULT_MAX_SENDS_PER_RUN)


def sends_today(now=None) -> int:
    """SENT messages since local midnight. Shadow runs consume none."""
    from openoutreach.signals.models import OutreachMessage

    now = now or timezone.now()
    return OutreachMessage.objects.filter(
        status=OutreachMessage.Status.SENT,
        sent_at__date=timezone.localtime(now).date()).count()


def capacity_consumed_today(now=None) -> int:
    """The daily-cap ledger: confirmed sends PLUS ambiguous attempts.

    An AMBIGUOUS failure may have been delivered — the recipient may be holding
    that email — so it conservatively consumes capacity for the day. Definitive
    failures (recipient refused, connection never opened) provably delivered
    nothing and do not.
    """
    from openoutreach.signals.models import OutreachMessage

    now = now or timezone.now()
    today = timezone.localtime(now).date()
    ambiguous = OutreachMessage.objects.filter(
        status=OutreachMessage.Status.SEND_FAILED,
        send_error__startswith="AMBIGUOUS",
        updated_at__date=today).count()
    return sends_today(now) + ambiguous


def last_successful_send_at():
    """When the most recent Atlas outreach send was accepted, or None. The
    persisted spacing anchor — no in-process state, so it works across cron
    invocations and worker restarts."""
    from openoutreach.signals.models import OutreachMessage

    latest = (OutreachMessage.objects.filter(status=OutreachMessage.Status.SENT)
              .exclude(sent_at=None).order_by("-sent_at").first())
    return latest.sent_at if latest else None


def spacing_wait_seconds(now=None) -> float:
    """Seconds until the minimum send spacing has elapsed; 0 = clear to send.
    Never slept through — a run that finds spacing unmet stops and lets the
    next cron invocation try."""
    now = now or timezone.now()
    last = last_successful_send_at()
    if last is None:
        return 0.0
    elapsed = (now - last).total_seconds()
    return max(0.0, min_seconds_between_sends() - elapsed)


# ── deterministic draft validation ───────────────────────────────────────────

#: Atlas's own price must not appear in a first touch (campaign rule, currently
#: enforced only in prompt prose). Deliberately narrow: dollar figures about
#: GRANTS are legitimate content, so this matches price-per-period shapes and
#: explicit pricing language, not every "$" in the body.
_PRICE_RE = re.compile(
    r"\$\s*\d[\d,.]*\s*(?:/|per\s+)(?:month|mo\b|year|yr\b|seat)"
    r"|founding (?:rate|price|pricing)"
    r"|\bour (?:price|pricing)\b"
    r"|\bcost to join\b",
    re.IGNORECASE)


def price_problems(body: str, *, first_touch: bool) -> list[str]:
    if first_touch and _PRICE_RE.search(body or ""):
        return ["names the price in a first touch — the campaign forbids price before "
                "the sequence earns it"]
    return []


def _booking_link_for(message) -> str:
    from openoutreach.core.models import Campaign

    if message.campaign_id and message.campaign and message.campaign.booking_link:
        return message.campaign.booking_link
    fallback = Campaign.objects.filter(
        name="Anansi Atlas — Founding Cohort").exclude(booking_link="").first()
    return fallback.booking_link if fallback else ""


def validate_draft(message, lead) -> list[str]:
    """Every deterministic reason this draft must not be sent automatically.

    Reuses the drafting command's own validators — the LLM's self-check is not
    a gate, these are. Empty list means the draft may move to "would send".
    """
    from openoutreach.core.management.commands.preview_cohort_drafts import (
        cta_problems,
        subject_problems,
    )

    problems: list[str] = []
    subject = (message.subject or "").strip()
    body = (message.body or "").strip()
    if not subject:
        problems.append("no subject")
    else:
        problems.extend(subject_problems(subject))
    if not body:
        problems.append("empty body")
        return problems
    booking = _booking_link_for(message)
    if not booking:
        # Fail closed: with no configured booking link there is no way to verify
        # the close has both real options, so autonomy may not vouch for it.
        problems.append("no campaign booking link configured — the CTA cannot be validated")
    else:
        problems.extend(cta_problems(body, booking))
    problems.extend(price_problems(body, first_touch=(message.sequence_position <= 1)))
    return problems


# ── draft freshness ──────────────────────────────────────────────────────────

def stale_draft_reason(draft, lead, *, last_sent_at=None) -> str:
    """Why this draft may not be used automatically, or "".

    A draft is evidence of a decision made at ``created_at``. Anything that
    changed the world after that moment — a touch actually going out, the
    disposition moving, a reply or bounce arriving — invalidates it for
    *automatic* use. Conservative on purpose: a human can still read and send
    a stale draft from the cockpit; the runner may not.
    """
    from openoutreach.signals.models import InboundMessage

    if last_sent_at and draft.created_at <= last_sent_at:
        return ("draft predates the most recent sent touch — it was written before "
                "the reader saw the previous email")
    if lead.disposition_at and draft.created_at <= lead.disposition_at:
        return "draft predates the lead's current disposition"
    latest_inbound = (InboundMessage.objects.filter(lead=lead)
                      .order_by("-ingested_at").first())
    if latest_inbound and draft.created_at <= latest_inbound.ingested_at:
        return "draft predates inbound mail from this lead — the context has changed"
    return ""


def usable_draft(lead, *, last_sent_at=None):
    """(draft, stale_reason). The newest DRAFTED row, and why it is unusable
    if it is. (None, "") means no draft exists at all."""
    from openoutreach.signals.models import OutreachMessage

    draft = (OutreachMessage.objects
             .filter(lead=lead, status=OutreachMessage.Status.DRAFTED)
             .order_by("-created_at").first())
    if draft is None:
        return None, ""
    reason = stale_draft_reason(draft, lead, last_sent_at=last_sent_at)
    return draft, reason


# ── per-lead evaluation ──────────────────────────────────────────────────────

def evaluate_lead(lead, *, now=None) -> Decision:
    """One explicit decision for one lead. Order matters: global suppression
    first, campaign gates next, sequence state, then the draft itself."""
    from openoutreach.signals.models import OutreachMessage, SalesLead
    from openoutreach.signals.unsubscribe import is_opted_out
    from openoutreach.core.management.commands.preview_cohort_drafts import research_gap

    now = now or timezone.now()

    if not (lead.email or "").strip():
        return Decision(SKIP_NO_EMAIL, "no email address on the lead", lead=lead)
    if is_opted_out(lead.email):
        return Decision(SKIP_OPTED_OUT, f"{lead.email} has a global opt-out", lead=lead)

    block = lead.cold_outreach_block()
    if block:
        if lead.disposition == SalesLead.DISPOSITION_DISQUALIFIED:
            return Decision(HOLD_DISQUALIFIED, block, lead=lead)
        if lead.disposition == SalesLead.DISPOSITION_REVIEW:
            return Decision(HOLD_REVIEW, block, lead=lead)
        return Decision(SKIP_TERMINAL, block, lead=lead)

    if lead.status in (SalesLead.Status.CALL_SCHEDULED, SalesLead.Status.CALL_DONE,
                       SalesLead.Status.NURTURING):
        return Decision(HOLD_IN_CONVERSATION,
                        f"pipeline status is {lead.get_status_display()} — a live "
                        "relationship, not a cold sequence", lead=lead)

    # A message whose delivery state is unknown freezes the lane. Both shapes:
    # an AMBIGUOUS-marked failure, and a SENDING claim that never finalized.
    ambiguous = (OutreachMessage.objects
                 .filter(lead=lead, status=OutreachMessage.Status.SEND_FAILED,
                         send_error__startswith="AMBIGUOUS").first())
    if ambiguous:
        return Decision(HOLD_AMBIGUOUS_SEND,
                        f"touch #{ambiguous.sequence_position} may already have been "
                        "delivered — verify the Sent folder by hand; automation never "
                        "retries an ambiguous send", lead=lead, message=ambiguous)
    stuck = (OutreachMessage.objects
             .filter(lead=lead, status=OutreachMessage.Status.SENDING).first())
    if stuck:
        return Decision(HOLD_AMBIGUOUS_SEND,
                        f"touch #{stuck.sequence_position} is claimed as SENDING and "
                        "never finalized — delivery state unknown", lead=lead, message=stuck)

    hold = lead.followup_hold()
    if hold:
        return Decision(HOLD_REPLIED, hold, lead=lead)

    sent = list(OutreachMessage.objects
                .filter(lead=lead, status=OutreachMessage.Status.SENT)
                .order_by("sent_at"))

    # History the automation cannot reason about: sends recorded before the
    # OutreachMessage era (email_status says sent, but no SENT row — or a SENT
    # row without a sent_at). Guessing a follow-up clock from that would count
    # from something other than a real delivery, which is exactly what the
    # timing rule forbids. These leads stay hand-run from the cockpit.
    if any(m.sent_at is None for m in sent):
        return Decision(HOLD_LEGACY_HISTORY,
                        "a sent touch has no sent_at timestamp (legacy row) — the "
                        "follow-up clock has no anchor; handle this lead by hand",
                        lead=lead)
    if not sent and lead.email_status == "sent":
        return Decision(HOLD_LEGACY_HISTORY,
                        "emailed before per-message records existed (email_status is "
                        "'sent' with no SENT OutreachMessage) — automation cannot know "
                        "what was said or when; handle this lead by hand", lead=lead)

    if sent:
        limit = max_touches()
        if len(sent) >= limit:
            return Decision(SKIP_ALREADY_SENT,
                            f"sequence complete — {len(sent)} of {limit} touches sent",
                            lead=lead)
        last = sent[-1]
        wait = followup_wait_days(len(sent))
        due_at = last.sent_at + timezone.timedelta(days=wait)
        if now < due_at:
            return Decision(SKIP_NOT_DUE,
                            f"touch #{len(sent) + 1} due {due_at.date()} "
                            f"({wait}d after the last sent touch)", lead=lead,
                            last_sent_at=last.sent_at)
        # The operator's manual date acts only as a brake, never an accelerator.
        if lead.next_follow_up and lead.next_follow_up > timezone.localtime(now).date():
            return Decision(SKIP_NOT_DUE,
                            f"operator hold-until {lead.next_follow_up} (next_follow_up)",
                            lead=lead, last_sent_at=last.sent_at)
        draft, stale = usable_draft(lead, last_sent_at=last.sent_at)
        if draft is None or stale:
            if research_gap(lead):
                return Decision(HOLD_RESEARCH, research_gap(lead), lead=lead)
            reason = stale or "no follow-up draft exists"
            return Decision(NEEDS_DRAFT, reason, lead=lead, last_sent_at=last.sent_at)
        problems = validate_draft(draft, lead)
        if problems:
            return Decision(INVALID_DRAFT, "; ".join(problems), lead=lead, message=draft)
        return Decision(WOULD_SEND_FOLLOWUP,
                        f"touch #{len(sent) + 1}, due since {due_at.date()}",
                        lead=lead, message=draft, last_sent_at=last.sent_at)

    # First touch.
    if research_gap(lead):
        return Decision(HOLD_RESEARCH, research_gap(lead), lead=lead)
    draft, stale = usable_draft(lead)
    if draft is None or stale:
        return Decision(NEEDS_DRAFT, stale or "no opener draft exists", lead=lead)
    problems = validate_draft(draft, lead)
    if problems:
        return Decision(INVALID_DRAFT, "; ".join(problems), lead=lead, message=draft)
    return Decision(WOULD_SEND_FIRST_TOUCH, "eligible, researched, drafted, validated",
                    lead=lead, message=draft)


# ── the campaign pass ────────────────────────────────────────────────────────

def evaluate_campaign(*, segment=None, now=None, assume_fresh=False) -> RunResult:
    """Evaluate every lead in the campaign segment and return ordered decisions.

    Freshness first, always: a stale/failed/never-synced mailbox yields exactly
    one system-level HOLD_MAILBOX_STALE decision and zero candidates — the
    runner enforces the invariant itself and never trusts cron ordering.
    ``assume_fresh`` exists for SHADOW diagnostics only (see the command).

    Priority: due follow-ups (oldest last-touch first), then first touches, both
    tie-broken by pk — stable, so queryset nondeterminism never chooses which
    organizations get mail. The daily cap then converts overflow candidates to
    SKIP_CAP_REACHED; capacity is counted from actual SENT rows, so shadow runs
    consume none.
    """
    from openoutreach.signals.ingest import mailbox_freshness_hold
    from openoutreach.signals.models import SalesLead

    now = now or timezone.now()
    segment = segment or SalesLead.Segment.COLD_FLORIDA_CRM

    result = RunResult()
    if not assume_fresh:
        hold = mailbox_freshness_hold(now)
        if hold:
            result.freshness_hold = hold
            result.decisions.append(Decision(HOLD_MAILBOX_STALE, hold))
            return result

    decisions = [evaluate_lead(lead, now=now)
                 for lead in SalesLead.objects.filter(list_segment=segment).order_by("pk")]

    followups = sorted((d for d in decisions if d.code == WOULD_SEND_FOLLOWUP),
                       key=lambda d: (d.last_sent_at, d.lead.pk))
    firsts = sorted((d for d in decisions if d.code == WOULD_SEND_FIRST_TOUCH),
                    key=lambda d: d.lead.pk)
    others = [d for d in decisions if d.code not in CANDIDATE_CODES]

    consumed = capacity_consumed_today(now)
    remaining = max(0, daily_send_limit() - consumed)
    ordered_candidates = followups + firsts
    for i, d in enumerate(ordered_candidates):
        if i >= remaining:
            d.code = SKIP_CAP_REACHED
            d.reason = (f"daily cap: {daily_send_limit()} allowed, {consumed} "
                        f"consumed today (sent + ambiguous), position {i + 1} in queue")

    result.decisions = ordered_candidates + others
    return result


# ── the atomic SENDING claim (live-phase infrastructure, built and tested now) ─

def claim_for_sending(message) -> bool:
    """Atomically claim one message for delivery. True = this caller owns it.

    A single conditional UPDATE, so two workers racing on the same row cannot
    both win — one matches the DRAFTED/SEND_FAILED predicate, the other finds
    the row already SENDING and matches nothing. AMBIGUOUS-marked failures are
    excluded at the same level: unclaimable by construction, not by convention.
    The claim carries no long transaction — the future live path claims, commits,
    then talks to SMTP outside any lock, then finalizes (the same Message-ID
    survives throughout because it lives on the row, minted at first attempt).
    """
    from openoutreach.signals.models import OutreachMessage

    updated = (OutreachMessage.objects
               .filter(pk=message.pk,
                       status__in=[OutreachMessage.Status.DRAFTED,
                                   OutreachMessage.Status.SEND_FAILED])
               .exclude(send_error__startswith="AMBIGUOUS")
               .update(status=OutreachMessage.Status.SENDING, updated_at=timezone.now()))
    return updated == 1


def hold_stuck_claims(*, now=None, max_age_minutes: int = STUCK_CLAIM_MINUTES) -> int:
    """Convert SENDING claims that never finalized into held AMBIGUOUS failures.

    A worker that died between claim and finalize leaves delivery state unknown
    — the mail may or may not have left. The only safe policy is the ambiguous
    one: mark it, hold it for a human, never auto-retry. Returns rows held.
    Called by the future live runner at startup; SHADOW never calls it (shadow
    never claims, so any stuck claim it sees belongs to someone else's crash and
    is *reported*, not mutated).
    """
    from openoutreach.signals.models import OutreachMessage

    now = now or timezone.now()
    cutoff = now - timezone.timedelta(minutes=max_age_minutes)
    return (OutreachMessage.objects
            .filter(status=OutreachMessage.Status.SENDING, updated_at__lt=cutoff)
            .update(status=OutreachMessage.Status.SEND_FAILED,
                    send_error="AMBIGUOUS — claimed for sending but never finalized "
                               "(worker died mid-send?). Delivery state unknown: check "
                               "the sending mailbox's Sent folder before any retry; a "
                               "retry reuses the same Message-ID."))


# ── the live delivery path (Gap 4B — built, tested, DISABLED in production) ──

def final_presend_block(message, *, now=None) -> str:
    """Why this claimed message may not go to SMTP after all, or "".

    The deterministic recheck that closes the race between queue construction
    and delivery: everything here is cheap (no AI, no network) and re-read from
    the database at the last moment. An opt-out, reply, terminal outcome, or
    disposition hold that landed after candidate selection stops the send here.
    """
    from openoutreach.signals import outreach
    from openoutreach.signals.models import OutreachMessage
    from openoutreach.signals.unsubscribe import is_opted_out

    message.refresh_from_db()
    if message.status != OutreachMessage.Status.SENDING:
        return f"message is no longer claimed (status: {message.status})"
    lead = message.lead
    lead.refresh_from_db()
    if not outreach.OUTREACH_MAILING_ADDRESS:
        return "OUTREACH_MAILING_ADDRESS is not set — CAN-SPAM footer unavailable"
    if is_opted_out(lead.email):
        return f"{lead.email} opted out since selection"
    block = lead.cold_outreach_block()
    if block:
        return block
    hold = lead.followup_hold()
    if hold:
        return hold
    if OutreachMessage.objects.filter(
            lead=lead, subject=message.subject.strip()[:300], body=message.body.rstrip(),
            status=OutreachMessage.Status.SENT).exists():
        return "this exact message was already sent"
    last_sent = (OutreachMessage.objects
                 .filter(lead=lead, status=OutreachMessage.Status.SENT)
                 .exclude(sent_at=None).order_by("-sent_at").first())
    stale = stale_draft_reason(message, lead,
                               last_sent_at=last_sent.sent_at if last_sent else None)
    if stale:
        return stale
    return ""


def autonomous_send(message, *, now=None) -> tuple[str, str]:
    """Deliver one claimed-eligible message. Returns (outcome code, detail).

    The Gap 3A carry-forward, realized: atomic SENDING claim → transaction
    already committed (the claim is a bare conditional UPDATE) → SMTP with NO
    database transaction held open → finalize. The manual cockpit path keeps
    its own lead-locked semantics; both build the wire message through
    ``outreach.build_outreach_email`` so SMTP behavior cannot drift.

    * A final-gate block after the claim reverts the row to DRAFTED — safe,
      because SMTP provably did not run.
    * The RFC Message-ID is minted (if absent) and persisted before SMTP, so
      the identity survives any failure and a later retry is the same logical
      message on the wire.
    * Failures reuse ``_bounded_send_error``: definitive → SEND_FAILED
      (retryable by claim, does not consume capacity), ambiguous → SEND_FAILED
      with the AMBIGUOUS prefix (unclaimable, consumes capacity, held for a
      human — never auto-retried).
    """
    from django.db import transaction

    from openoutreach.signals import outreach
    from openoutreach.signals.models import OutreachMessage

    if not claim_for_sending(message):
        return (LIVE_BLOCKED_FINAL_GATE,
                "could not claim — another worker owns it or it is unclaimable")
    block = final_presend_block(message, now=now)
    if block:
        OutreachMessage.objects.filter(
            pk=message.pk, status=OutreachMessage.Status.SENDING).update(
            status=OutreachMessage.Status.DRAFTED)
        return (LIVE_BLOCKED_FINAL_GATE, block)

    lead = message.lead
    if not message.message_id:
        message.message_id = outreach._mint_message_id(outreach.from_address_for(lead))
        message.save(update_fields=["message_id", "updated_at"])

    body = message.body.rstrip()
    subject = message.subject.strip()
    email, cc_list = outreach.build_outreach_email(lead, subject, body, "", message.message_id)
    # No transaction is open here: the SMTP call happens against a committed
    # SENDING claim, so a worker death leaves a visible stuck claim (recovered
    # by hold_stuck_claims), never an invisible rollback.
    try:
        email.send(fail_silently=False)
    except Exception as exc:  # noqa: BLE001 — every failure must leave a record
        err = outreach._bounded_send_error(exc)
        message.status = OutreachMessage.Status.SEND_FAILED
        message.send_error = err
        message.sent_at = None
        message.save(update_fields=["status", "send_error", "sent_at", "updated_at"])
        if err.startswith("AMBIGUOUS"):
            return (LIVE_AMBIGUOUS, err)
        return (LIVE_SEND_FAILED, err)
    with transaction.atomic():
        outreach.record_successful_send(message, lead, subject, body, cc_list)
    return (LIVE_SENT, "")
