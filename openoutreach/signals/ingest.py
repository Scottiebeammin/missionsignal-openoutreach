"""Inbound mail ingestion — Stage A: deterministic observation and correlation.

Gap 3B's core. This module never talks to Gmail; it consumes ``FetchedMessage``
values from a transport (see ``gmail_transport.py`` for the real one) so every
rule here is testable without a mailbox. It is also strictly an observer: nothing
in this module — or in the transport interface it consumes — can move, archive,
label, mark read, delete, or answer mail.

Two-stage design, deliberately:

* **Stage A (this module)** is deterministic: does this event exist, whose is it,
  which Atlas touch does it answer, and is it a human reply / bounce /
  autoresponder / Marcus's own reply. Safety state changes happen HERE — a
  correlated human reply pauses cold automation the moment it is stored.
* **Stage B (semantic classification — pricing, anger, intent)** is a later
  layer. Its absence, failure, or low confidence must not weaken Stage A, so the
  default classification for a real human reply is ``human_reply_unclassified``
  with ``needs_attention=True``: paused, visible, and waiting for Marcus.

Scope filter: Marcus's mailbox is his own. Only messages plausibly related to
Atlas outreach are ever stored — see ``_relevance`` for the exact rule. Anything
else is counted as skipped and never persisted.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from django.utils import timezone

logger = logging.getLogger(__name__)

#: Bodies are normalized text for correlation/display, not an archive. Capped so
#: a giant HTML mail cannot bloat the table.
BODY_CAP = 20_000

#: How far back the address/recency fallback will attribute a reply to the most
#: recent sent touch. Outside this window an un-threaded mail from a known lead
#: still ingests, but unresolved — attribution is a guess we refuse to make.
FALLBACK_WINDOW_DAYS = 60


@dataclass
class FetchedMessage:
    """One message as handed over by a transport. Headers only + normalized text."""

    gmail_id: str
    thread_id: str = ""
    rfc_message_id: str = ""
    in_reply_to: str = ""
    references: str = ""
    from_address: str = ""
    to_addresses: str = ""
    subject: str = ""
    date: object = None                    # datetime or None
    body_text: str = ""
    #: Raw header pairs the classifier needs (Auto-Submitted, X-Failed-Recipients,
    #: Content-Type). Never the full raw message.
    headers: dict = field(default_factory=dict)


@dataclass
class IngestStats:
    fetched: int = 0
    stored: int = 0
    duplicates: int = 0
    skipped_irrelevant: int = 0
    replies: int = 0
    bounces: int = 0
    autoresponders: int = 0
    outbound_human: int = 0
    unresolved: int = 0
    errors: int = 0


# ── header helpers ──────────────────────────────────────────────────────────

_MSGID_RE = re.compile(r"<[^<>\s]+>")


def _message_ids(value: str) -> list[str]:
    """All RFC message-ids in a header value, angle brackets preserved."""
    return _MSGID_RE.findall(value or "")


def _addr(value: str) -> str:
    """The bare address out of 'Display Name <addr@host>' — lowercased."""
    m = re.search(r"<([^<>]+)>", value or "")
    raw = m.group(1) if m else (value or "")
    return raw.strip().lower()


def _is_dsn(msg: FetchedMessage) -> bool:
    """Delivery-status notification, detected from standard signatures only."""
    sender = _addr(msg.from_address)
    if sender.startswith(("mailer-daemon@", "postmaster@")):
        return True
    ctype = (msg.headers.get("Content-Type") or "").lower()
    return "report-type=delivery-status" in ctype


def _is_autoresponder(msg: FetchedMessage) -> bool:
    """Automated reply, from headers first (RFC 3834), subject as fallback.

    ``Precedence: bulk`` alone is deliberately NOT used — newsletters carry it.
    """
    auto_submitted = (msg.headers.get("Auto-Submitted") or "").lower()
    if auto_submitted and auto_submitted != "no":
        return True
    if msg.headers.get("X-Autoreply") or msg.headers.get("X-Autorespond"):
        return True
    subject = (msg.subject or "").lower()
    return subject.startswith(("automatic reply", "auto reply", "auto-reply", "out of office"))


#: A reply that says this, and near-only this, is an unsubscribe by other means.
#: Kept deliberately narrow: matching is on a SHORT body so "please don't remove
#: me from consideration" in a long reply can't trigger it.
_REMOVAL_RE = re.compile(
    r"\b(remove me|unsubscribe|take me off|stop emailing|do not (email|contact) (me|us))\b",
    re.IGNORECASE)


def _looks_like_removal(body: str) -> bool:
    text = (body or "").strip()
    return len(text) <= 300 and bool(_REMOVAL_RE.search(text))


#: DSN status extraction: "Status: 5.1.1" (RFC 3464) or a leading SMTP 550-class
#: code in the text. 5.x.x = permanent, 4.x.x = transient.
_DSN_STATUS_RE = re.compile(r"\bStatus:\s*([45])\.\d+\.\d+", re.IGNORECASE)
_SMTP_CODE_RE = re.compile(r"\b([45])5\d\b|\b([45])\d\d[ -]\d\.\d+\.\d+")


def _dsn_severity(msg: FetchedMessage) -> str:
    """'hard', 'soft', or 'unknown' — from the DSN's own machine-readable parts."""
    m = _DSN_STATUS_RE.search(msg.body_text or "")
    if m:
        return "hard" if m.group(1) == "5" else "soft"
    m = _SMTP_CODE_RE.search(msg.body_text or "")
    if m:
        digit = m.group(1) or m.group(2)
        return "hard" if digit == "5" else "soft"
    return "unknown"


def _dsn_failed_recipient(msg: FetchedMessage) -> str:
    """The address the DSN says failed, from its standard fields."""
    explicit = _addr(msg.headers.get("X-Failed-Recipients") or "")
    if explicit:
        return explicit
    m = re.search(r"Final-Recipient:\s*rfc822;\s*([^\s;]+)", msg.body_text or "", re.IGNORECASE)
    return m.group(1).strip().lower() if m else ""


# ── correlation ─────────────────────────────────────────────────────────────

def correlate(msg: FetchedMessage, *, mailbox: str):
    """(lead, outreach_message, how) for a fetched message.

    The hierarchy, most reliable first — and NEVER a guess:

    1. exact ``In-Reply-To`` == a stored ``OutreachMessage.message_id``;
    2. any ``References`` token == a stored ``message_id``;
    3. provider thread: this Gmail thread already contains a correlated message;
    4. conservative fallback: the From address matches exactly ONE SalesLead, and
       that lead has a SENT touch within FALLBACK_WINDOW_DAYS — attributed to the
       latest such touch;
    5. unresolved. Ambiguity (two leads sharing an address, no recent touch)
       lands here on purpose: an unattached message is recoverable, a message
       attached to the wrong nonprofit is not.
    """
    from openoutreach.signals.models import InboundMessage, OutreachMessage, SalesLead

    Corr = InboundMessage.Correlation

    for candidate in _message_ids(msg.in_reply_to):
        om = OutreachMessage.objects.filter(message_id=candidate).select_related("lead").first()
        if om:
            return om.lead, om, Corr.IN_REPLY_TO
    for candidate in _message_ids(msg.references):
        om = OutreachMessage.objects.filter(message_id=candidate).select_related("lead").first()
        if om:
            return om.lead, om, Corr.REFERENCES
    if msg.thread_id:
        sibling = (InboundMessage.objects
                   .filter(thread_id=msg.thread_id, lead__isnull=False)
                   .exclude(correlation=Corr.UNRESOLVED)
                   .select_related("lead", "outreach_message").first())
        if sibling:
            return sibling.lead, sibling.outreach_message, Corr.THREAD
    sender = _addr(msg.from_address)
    if sender:
        leads = list(SalesLead.objects.filter(email__iexact=sender)[:2])
        if len(leads) == 1:
            cutoff = timezone.now() - timezone.timedelta(days=FALLBACK_WINDOW_DAYS)
            om = (OutreachMessage.objects
                  .filter(lead=leads[0], status=OutreachMessage.Status.SENT,
                          sent_at__gte=cutoff)
                  .order_by("-sent_at").first())
            if om:
                return leads[0], om, Corr.ADDRESS_FALLBACK
            return leads[0], None, Corr.ADDRESS_FALLBACK
    return None, None, Corr.UNRESOLVED


def _relevance(msg: FetchedMessage, *, mailbox: str) -> str:
    """Why this message belongs in Atlas at all, or "" to skip it.

    Marcus's inbox is his own; the filter is allow-list, not deny-list. A message
    is ingested only if it is (a) threaded onto an Atlas send, (b) from an address
    we hold as a lead, (c) a delivery-status notification, or (d) the mailbox
    owner himself writing to a lead address (his manual reply). Everything else —
    newsletters, personal mail, vendor mail — is skipped unseen.
    """
    from openoutreach.signals.models import OutreachMessage, SalesLead

    ids = set(_message_ids(msg.in_reply_to)) | set(_message_ids(msg.references))
    if ids and OutreachMessage.objects.filter(message_id__in=ids).exists():
        return "threaded"
    if _is_dsn(msg):
        return "dsn"
    sender = _addr(msg.from_address)
    if sender and SalesLead.objects.filter(email__iexact=sender).exists():
        return "lead_sender"
    if sender == (mailbox or "").lower():
        recipients = [_addr(part) for part in (msg.to_addresses or "").split(",")]
        if SalesLead.objects.filter(email__in=[r for r in recipients if r]).exists():
            return "owner_to_lead"
    return ""


# ── the pipeline ────────────────────────────────────────────────────────────

def ingest_message(msg: FetchedMessage, *, mailbox: str, owner: str) -> tuple[object, str]:
    """Ingest one fetched message. Returns (InboundMessage|None, disposition).

    Idempotent by (mailbox, gmail_id): re-reading the same message is a no-op —
    including its state transitions, which only run on first insert.
    """
    from openoutreach.signals.models import InboundMessage, SalesLead, upgrade_outcome

    if InboundMessage.objects.filter(mailbox=mailbox, gmail_id=msg.gmail_id).exists():
        return None, "duplicate"

    why = _relevance(msg, mailbox=mailbox)
    if not why:
        return None, "irrelevant"

    sender = _addr(msg.from_address)
    lead, om, how = correlate(msg, mailbox=mailbox)

    # Deterministic classification, most specific first.
    if _is_dsn(msg):
        severity = _dsn_severity(msg)
        classification = {
            "hard": InboundMessage.Classification.BOUNCE_HARD,
            "soft": InboundMessage.Classification.BOUNCE_SOFT,
        }.get(severity, InboundMessage.Classification.DSN_UNRESOLVED)
        direction = InboundMessage.Direction.INBOUND
        # A DSN's In-Reply-To rarely helps; its embedded failed-recipient does.
        if lead is None:
            failed = _dsn_failed_recipient(msg)
            if failed:
                leads = list(SalesLead.objects.filter(email__iexact=failed)[:2])
                if len(leads) == 1:
                    lead, how = leads[0], InboundMessage.Correlation.ADDRESS_FALLBACK
    elif sender == (owner or "").lower():
        classification = InboundMessage.Classification.OUTBOUND_HUMAN
        direction = InboundMessage.Direction.OUTBOUND_HUMAN
    elif _is_autoresponder(msg):
        classification = InboundMessage.Classification.AUTORESPONDER
        direction = InboundMessage.Direction.INBOUND
    elif _looks_like_removal(msg.body_text):
        classification = InboundMessage.Classification.REMOVAL_REQUEST
        direction = InboundMessage.Direction.INBOUND
    else:
        classification = InboundMessage.Classification.HUMAN_REPLY_UNCLASSIFIED
        direction = InboundMessage.Direction.INBOUND

    C = InboundMessage.Classification
    record = InboundMessage.objects.create(
        lead=lead,
        outreach_message=om,
        mailbox=mailbox,
        direction=direction,
        classification=classification,
        correlation=how,
        gmail_id=msg.gmail_id,
        thread_id=msg.thread_id,
        rfc_message_id=(msg.rfc_message_id or "")[:300],
        in_reply_to=(msg.in_reply_to or "")[:300],
        references_header=msg.references or "",
        from_address=(msg.from_address or "")[:320],
        to_addresses=(msg.to_addresses or "")[:500],
        subject=(msg.subject or "")[:500],
        header_date=msg.date if hasattr(msg.date, "tzinfo") else None,
        body_text=(msg.body_text or "")[:BODY_CAP],
        # Every real human reply needs Marcus until a later classification layer
        # exists; a removal request doubly so (compliance); an unresolved DSN is a
        # delivery problem someone should look at. OOO and Marcus's own replies
        # are informational.
        needs_attention=classification in (
            C.HUMAN_REPLY_UNCLASSIFIED, C.REMOVAL_REQUEST, C.DSN_UNRESOLVED),
    )

    # ── Stage A safety transitions — deterministic, first-insert only ────────
    if lead is not None:
        if classification in (C.HUMAN_REPLY_UNCLASSIFIED, C.REMOVAL_REQUEST):
            # A real human reply pauses cold automation FIRST; what the reply
            # means is a later question. REPLIED feeds followup_hold(), which the
            # automated drafting path already consults; the outcome ladder means
            # later bookkeeping cannot downgrade this back to awaiting.
            upgrade_outcome(lead, SalesLead.Outcome.REPLIED)
        elif classification == C.BOUNCE_HARD:
            # Terminal via the existing gate. Deliberately NOT an EmailOptOut:
            # a dead address is not a person asking to be left alone.
            upgrade_outcome(lead, SalesLead.Outcome.BOUNCED)
        # Soft/unresolved DSNs and autoresponders change no state: a full mailbox
        # is not a refusal, and an OOO is not an answer.

    return record, "stored"


def ingest_mailbox(transport, *, mailbox: str, owner: str) -> IngestStats:
    """Poll one mailbox through a transport and ingest everything new.

    Cursor discipline: the checkpoint advances only after every fetched message
    has been processed without an unexpected error — a failed run re-reads, and
    idempotency makes the re-read free. A failed run must never skip mail.
    """
    from openoutreach.signals.models import InboundMessage, MailboxCursor

    cursor, _ = MailboxCursor.objects.get_or_create(mailbox=mailbox)
    cursor.last_run_at = timezone.now()
    stats = IngestStats()
    try:
        messages, new_history_id = transport.fetch_new(cursor.history_id)
    except Exception as exc:  # noqa: BLE001 — a dead mailbox must not kill the cron
        cursor.last_error = f"{type(exc).__name__}: {exc}"[:500]
        cursor.save()
        stats.errors += 1
        logger.exception("ingest: fetch failed for %s", mailbox)
        return stats

    failed = False
    for msg in messages:
        stats.fetched += 1
        try:
            record, disposition = ingest_message(msg, mailbox=mailbox, owner=owner)
        except Exception:  # noqa: BLE001
            stats.errors += 1
            failed = True
            logger.exception("ingest: message %s failed in %s", msg.gmail_id, mailbox)
            continue
        if disposition == "duplicate":
            stats.duplicates += 1
        elif disposition == "irrelevant":
            stats.skipped_irrelevant += 1
        else:
            stats.stored += 1
            C = InboundMessage.Classification
            if record.classification in (C.HUMAN_REPLY_UNCLASSIFIED, C.REMOVAL_REQUEST):
                stats.replies += 1
            elif record.classification in (C.BOUNCE_HARD, C.BOUNCE_SOFT, C.DSN_UNRESOLVED):
                stats.bounces += 1
            elif record.classification == C.AUTORESPONDER:
                stats.autoresponders += 1
            elif record.classification == C.OUTBOUND_HUMAN:
                stats.outbound_human += 1
            if record.correlation == InboundMessage.Correlation.UNRESOLVED:
                stats.unresolved += 1

    if not failed:
        # Advance only on a fully clean pass over what was fetched.
        cursor.history_id = new_history_id or cursor.history_id
        cursor.last_success_at = timezone.now()
        cursor.last_error = ""
    else:
        cursor.last_error = "one or more messages failed to ingest — cursor held"
    cursor.save()
    return stats
