"""
Server-side outreach composer + send helper for the operator cockpit.

Deterministic draft generation (no LLM required) so the outreach queue always
has a solid starting email the operator can edit before sending. Mirrors the
retired n8n composer's warm/cold template — sales walkthrough video, offer, and
a soft CTA — but lives on the server so review-edit-send happens in one place.
"""
import logging
import os
import re
import smtplib
from email.utils import make_msgid

from django.conf import settings
from django.core.mail import EmailMessage
from django.db import transaction
from django.utils import timezone

from openoutreach.signals.models import SalesLead

logger = logging.getLogger(__name__)

_WARMTH_RANK = {"hot": 0, "warm": 1, "reconnect": 2, "cold": 3}


def outreach_queue():
    """Leads still to email. Marcus's hand-written drafts surface first (so the
    cockpit opens on his real emails, not auto-composed ones), then by segment
    (warm before cold), warmth, and org."""
    leads = list(SalesLead.objects.filter(email_status="not_sent").exclude(email=""))
    leads.sort(key=lambda l: (
        0 if l.outreach_draft else 1,          # hand-written drafts first
        0 if l.list_segment == "warm" else 1,
        _WARMTH_RANK.get(l.warmth, 9),
        (l.organization or "").casefold(),
    ))
    return leads


def _links():
    return {
        "video": os.getenv("WALKTHROUGH_VIDEO_URL", "https://youtu.be/FBvLg9c35Qo"),
        "signup": os.getenv("STRIPE_MONTHLY_URL", "https://anansiatlas.com/anansi-atlas/"),
        "annual": os.getenv("STRIPE_ANNUAL_URL", "https://buy.stripe.com/eVqdR86XU4XwfZB2ANbV604"),
        "cal": os.getenv("SCHEDULING_URL", "https://cal.com/marcus-scott-br7maf/founder-walkthrough"),
    }


_LEGAL_SUFFIXES = (" incorporated", " inc.", " inc", " corp.", " corp", " llc", " co.", " ltd.", " ltd")


def _display_org(name: str) -> str:
    """Drop trailing legal suffixes so 'Arnette House Inc' reads as 'Arnette House'."""
    n = (name or "").strip().rstrip(".,")
    low = n.lower()
    for suffix in _LEGAL_SUFFIXES:
        if low.endswith(suffix):
            return n[: len(n) - len(suffix)].rstrip(" ,.").strip() or "your organization"
    return n or "your organization"


def _greeting_first(lead) -> str:
    """First name to greet with — only when the lead's name is a real contact
    person (not just the org name repeated), otherwise a neutral 'there'."""
    name = (lead.name or "").strip()
    org = (lead.organization or "").strip()
    if name and name.casefold() != org.casefold():
        return name.split(" ")[0]
    return "there"


def compose_outreach_email(lead) -> tuple[str, str]:
    """Return (subject, body) for a lead — the editable starting draft."""
    first = _greeting_first(lead)
    org = _display_org(lead.organization)
    warm = lead.list_segment == "warm"
    links = _links()

    if warm:
        opening = (
            f"Hi {first},\n\nIt's Marcus — {lead.why_fit.strip()}."
            if lead.why_fit else
            f"Hi {first},\n\nIt's Marcus — it's been a minute."
        )
        if lead.focus_area:
            opening += f"\n\n{lead.focus_area.strip()}"
    else:
        opening = (
            f"Hi {first},\n\n"
            f"I'm Marcus Scott, founder of Anansi Atlas here in Central Florida. I'm reaching out "
            f"because {org} is doing meaningful work in the community, and I wanted to show you some "
            f"of the opportunities that may already be surrounding your mission — the kind that can "
            f"keep pushing it forward."
        )

    lines = [
        opening,
        "",
        "Anansi Atlas was built to support organizations like yours: it maps the full web of "
        "opportunity around your mission — aligned funders, strategic partners, government pathways, "
        "and free capacity-building resources — and turns it into a clear brief with a readiness read "
        "and a practical 30-day action plan.",
        "",
        "Here's a quick 3-minute look at the actual platform — not a pitch deck, the real thing:",
        links["video"],
        "",
        "If it feels like a fit, you can claim a founding seat here:",
        links["signup"],
        "",
        "The founding seat is $150/month, locked in for life.",
    ]
    if links["annual"]:
        lines += ["There's also an annual option at $1,440/year, which saves 20%:", links["annual"]]
    if links["cal"]:
        lines += ["", "Or, if you'd rather walk through it first, grab 45 minutes with me here:", links["cal"]]
    lines += [
        "",
        f"Either way, I appreciate the work {org} is doing in the community.",
        "",
        "Best,",
        "Marcus Scott",
        "Anansi Atlas · The Web of Opportunity",
        f"{OUTREACH_WEBSITE} · {OUTREACH_LINKEDIN}",
    ]

    subject = lead.subject_line.strip() if lead.subject_line else f"Thought of {org} while building this"
    return subject, "\n".join(lines)


def draft_for(lead) -> tuple[str, str]:
    """The draft to show in the cockpit: the operator's saved edit if present,
    otherwise a freshly composed draft."""
    subject, body = compose_outreach_email(lead)
    if lead.outreach_draft:
        body = lead.outreach_draft
    return subject, body


def compose_call_script(lead, contact_name: str = "") -> str:
    """Short, personalized phone script (opener + voicemail) for a Call List
    lead — stored on the lead so it's right there when the operator dials.
    Full playbook: anansi-atlas-sales-playbook/CALL-SCRIPT.md."""
    org = lead.organization or "your organization"
    county = (lead.region or "").strip()
    where = f"{county} County" if county else "your area"
    first = (contact_name or "").split(" ")[0].strip()
    greet = first or "there"
    cal = os.getenv("SCHEDULING_URL", "https://cal.com/marcus-scott-br7maf/founder-walkthrough")
    who = contact_name.strip() if contact_name else "ask for whoever handles grants & funding"
    return "\n".join([
        f"📞 CALL SCRIPT — {org}",
        f"Contact: {who}   ·   Book: {cal}",
        "",
        "LIVE OPENER (~20 sec, then LISTEN):",
        f'"Hi {greet}, this is Marcus Scott — founder of Anansi Atlas, here in '
        f"Central Florida, and I'll be quick. I built a platform that maps the "
        f"funders, partners, and free resources already aligned with a nonprofit's "
        f"mission. I came across {org} while mapping {where} and thought of you all. "
        f'Is finding aligned funders something on your plate right now?"',
        "",
        "VOICEMAIL (~30 sec — no price, no callback ask):",
        f'"Hi {greet}, this is Marcus Scott, founder of Anansi Atlas here in Central '
        f"Florida. I came across {org} while mapping the funders aligned with missions "
        f"like yours in {where}, and thought it'd be genuinely useful. No pitch — I'd "
        f'just love to show you a 3-minute look. I\'m at anansiatlas.com. Thanks for what you do."',
        "",
        "IF INTERESTED → get their email + book the 15-min walkthrough.",
        "RULE: Atlas *maps & surfaces* funders — never \"gets you grants.\" Snapshot isn't free.",
    ])


OUTREACH_BCC = os.getenv("OUTREACH_BCC_EMAIL", "")
# marcus@ rides on CC, not BCC, so the recipient can see him and reply-all
# reaches him directly. Set OUTREACH_CC_EMAIL to "" to drop the visible copy and
# OUTREACH_BCC_EMAIL to put it back on BCC instead — an address in both is only
# CC'd, never doubled.
OUTREACH_CC = os.getenv("OUTREACH_CC_EMAIL", "marcus@anansiatlas.com")
OUTREACH_WEBSITE = os.getenv("OUTREACH_WEBSITE", "anansiatlas.com")
# CAN-SPAM requires a valid physical postal address on every commercial email.
# Set OUTREACH_MAILING_ADDRESS in the Render environment (a USPS PO box, a
# private mailbox, or the registered agent address all qualify). While it is
# empty, send_outreach_email refuses to send rather than sending unlawfully.
OUTREACH_MAILING_ADDRESS = os.getenv("OUTREACH_MAILING_ADDRESS", "").strip()
OUTREACH_LINKEDIN = os.getenv("OUTREACH_LINKEDIN_URL", "linkedin.com/company/anansi-atlas")


def from_address_for(lead) -> str:
    """All outreach sends from the main sending mailbox (DEFAULT_FROM_EMAIL, mail@,
    DKIM-signed), which keeps cold-send volume off marcus@'s sender reputation.
    marcus@ is CC'd (visible to the recipient, and reply-all reaches him) and is
    also the Reply-To, so marcus@ is the single pane for the whole trail without
    being the send-from address. Env-override OUTREACH_FROM_EMAIL."""
    return os.getenv("OUTREACH_FROM_EMAIL", settings.DEFAULT_FROM_EMAIL)


_FREEMAIL = {
    "gmail.com", "yahoo.com", "aol.com", "hotmail.com", "outlook.com", "icloud.com",
    "me.com", "msn.com", "earthlink.net", "centurylink.net", "embarqmail.com",
    "att.net", "comcast.net", "bellsouth.net", "verizon.net", "sbcglobal.net",
}


def org_website(lead):
    """Best-effort organization website for a lead so the operator can eyeball
    the org before sending. Uses the email's domain (e.g. info@arnettehouse.org
    → arnettehouse.org); for a personal/free-mail address (or no email) it falls
    back to a web search for the org name. Returns a dict {url, label, search} or
    None. Best-effort — a link to verify, not a verified claim."""
    from urllib.parse import quote_plus
    email = (lead.email or "").strip()
    org = (lead.organization or "").strip()
    domain = email.split("@")[-1].lower() if "@" in email else ""
    if domain and domain not in _FREEMAIL:
        return {"url": f"https://{domain}", "label": domain, "search": False}
    if org:
        return {"url": f"https://www.google.com/search?q={quote_plus(org)}", "label": "search the web", "search": True}
    return None


def parse_cc(cc_emails: str) -> list[str]:
    """Split a comma/semicolon/space-separated CC string into clean addresses."""
    parts = re.split(r"[,;\s]+", (cc_emails or "").strip())
    return [p for p in (x.strip() for x in parts) if "@" in p]


def advance_to_contacted(lead) -> None:
    """Move a brand-new lead's pipeline stage to Reached Out when we contact them.
    Only advances from NEW, so it never knocks back a lead already further along
    (call scheduled/done, closed, nurturing) or intentionally set aside (passed).
    Mutates in place; the caller saves with "status" in update_fields."""
    if lead.status == SalesLead.Status.NEW:
        lead.status = SalesLead.Status.REACHED_OUT


def compliance_footer(email: str) -> str:
    """The CAN-SPAM block: who sent it, where they are, and how to stop it."""
    from openoutreach.signals.unsubscribe import unsubscribe_url

    return "\n".join([
        "",
        "—",
        f"Anansi Atlas · Scott Foundry Group LLC · {OUTREACH_MAILING_ADDRESS}",
        f"Prefer not to hear from me? Unsubscribe here: {unsubscribe_url(email)}",
    ])


def _mint_message_id(from_address: str) -> str:
    """A unique RFC-5322 Message-ID anchored to the sending domain.

    Ported from the Deal world's ``emails/sender.py`` — the pattern, not the module,
    since the two send paths stay separate. Anchoring to the From domain (rather than
    ``make_msgid``'s default of the local hostname) keeps the ID aligned with the
    sender instead of leaking the Render container hostname, and gives inbound reply
    correlation a stable value to match ``In-Reply-To``/``References`` against.
    """
    domain = (from_address or "").rsplit("@", 1)[-1] or "anansiatlas.com"
    return make_msgid(domain=domain)


#: Exception types after which the mail MAY have been delivered even though the
#: call failed — the server can accept the DATA and the response still be lost.
#: These are recorded distinctly so a human verifies before retrying.
_AMBIGUOUS_SMTP_ERRORS = (TimeoutError, ConnectionError, smtplib.SMTPServerDisconnected)


def _bounded_send_error(exc: Exception) -> str:
    """A persisted description of a send failure: class + message, capped.

    Capped so a chatty server can't bloat the row, and built only from the
    exception itself — SMTP exceptions carry server replies, never our credentials.
    Ambiguous-delivery failures are prefixed so the operator knows a retry might
    double-deliver, and that the retry will reuse the same Message-ID.
    """
    text = f"{type(exc).__name__}: {exc}"[:400]
    if isinstance(exc, _AMBIGUOUS_SMTP_ERRORS):
        return ("AMBIGUOUS — the server may have accepted this before the connection "
                "died, so it MAY have been delivered. Check the sending mailbox's Sent "
                "folder before retrying; a retry reuses the same Message-ID. " + text)[:500]
    return text[:500]


def _claim_outreach_message(lead, subject: str, body: str):
    """The OutreachMessage row this send attempt belongs to. Never returns None.

    Claim order:
    1. An existing row with this exact subject+body in DRAFTED or SEND_FAILED — the
       retry case. Reusing it keeps the pre-minted Message-ID, so a retry after an
       ambiguous timeout is the *same* logical message on the wire, not a new
       identity for a mail the recipient may already have.
    2. The most recent DRAFTED row — the normal case; the cockpit's edits to
       subject/body are edits of that draft, so it is updated to what actually goes
       out (the angle chosen at drafting time survives).
    3. A new row — a hand-written cockpit send that never went through drafting.
       Sequence position continues from the last SENT touch, so follow-up logic
       still sees an ordered history; no angle is claimed because none was chosen.
    """
    from openoutreach.signals.models import OutreachMessage

    subject = subject.strip()[:300]
    msg = (OutreachMessage.objects
           .filter(lead=lead, subject=subject, body=body,
                   status__in=[OutreachMessage.Status.DRAFTED, OutreachMessage.Status.SEND_FAILED])
           .order_by("-created_at").first())
    if msg is None:
        msg = (OutreachMessage.objects
               .filter(lead=lead, status=OutreachMessage.Status.DRAFTED)
               .order_by("-created_at").first())
    if msg is None:
        prior = (OutreachMessage.objects
                 .filter(lead=lead, status=OutreachMessage.Status.SENT)
                 .order_by("-sent_at", "-created_at").first())
        msg = OutreachMessage(
            lead=lead,
            genre=(OutreachMessage.Genre.COLD_FOLLOWUP if prior else OutreachMessage.Genre.COLD_OPENER),
            sequence_position=(prior.sequence_position + 1) if prior else 1,
        )
    msg.subject = subject
    msg.body = body
    return msg


def send_outreach_email(lead, subject: str, body: str, cc: str = "") -> None:
    """Send one outreach email to the lead, record it, and advance the pipeline.

    Sends from the main mailbox (see from_address_for) with marcus@ CC'd; Reply-To
    (marcus@) is stamped by the email backend. Raises on failure so the caller can
    surface it — the lead is marked sent only on success.

    Concurrency: the whole attempt runs inside one transaction holding a
    ``select_for_update`` lock on the **SalesLead row**. The lead is the right thing
    to lock because every guard consulted here (email_status, disposition, outcome,
    the duplicate check) lives on or hangs off the lead — locking only the
    OutreachMessage would still let two workers each claim a different row and both
    deliver. Serialization means holding the lock across the SMTP call (bounded by
    EMAIL_TIMEOUT); at one lead per send that contention is confined to the one row
    that must not race. The in-transaction duplicate check — an identical
    subject+body already SENT — is what actually refuses the second of two
    concurrent attempts once the first commits.

    Failure: the SMTP exception is caught *inside* the transaction and re-raised
    *after* it commits, so the SEND_FAILED status, the bounded ``send_error``, and
    the pre-minted Message-ID all survive. Raising inside the atomic block would
    roll them back — a failed send would leave no trace, and a retry would mint a
    new identity for a message the recipient might already have (see
    ``_bounded_send_error`` for the ambiguous-timeout case; there is deliberately
    no auto-retry — an ambiguous failure holds for a human to verify).
    """
    from openoutreach.signals.models import OutreachMessage, SalesLead
    from openoutreach.signals.unsubscribe import is_opted_out

    send_exc: Exception | None = None
    with transaction.atomic():
        lead = SalesLead.objects.select_for_update().get(pk=lead.pk)

        # A rule enforced at the only place mail leaves the system, so no future
        # caller can route around it.
        if is_opted_out(lead.email):
            raise ValueError(
                f"{lead.email} has opted out of outreach — not sending. "
                "Remove them from the batch; do not re-add the address."
            )
        # The authoritative disposition/outcome gate. It lives here, next to the
        # opt-out check, because this is the only function every send goes through —
        # a gate in the drafting command is a gate one `--lead N` walks straight past.
        block = lead.cold_outreach_block()
        if block:
            raise ValueError(
                f"{lead.organization or lead.email} is {block} — not sending. "
                "Resolve the disposition on the lead before sending, rather than routing "
                "around this check."
            )
        if not OUTREACH_MAILING_ADDRESS:
            raise ValueError(
                "OUTREACH_MAILING_ADDRESS is not set. CAN-SPAM requires a valid physical "
                "postal address on commercial email — set it in the Render environment "
                "(a USPS PO box or the registered agent address qualifies) before sending."
            )
        body = body.rstrip()
        # The concurrency backstop: if this exact message already went out, refuse.
        # Under the lead lock this is what stops the second of two concurrent
        # identical attempts — the first commits its SENT row, the second sees it.
        if OutreachMessage.objects.filter(
                lead=lead, subject=subject.strip()[:300], body=body,
                status=OutreachMessage.Status.SENT).exists():
            raise ValueError(
                f"this exact message was already sent to {lead.email} — not sending it "
                "twice. Draft a new touch if another email is intended."
            )

        # Claim the message row and mint its Message-ID BEFORE the SMTP call, so the
        # identity is durable even if the connection dies mid-send.
        msg = _claim_outreach_message(lead, subject, body)
        if not msg.message_id:
            msg.message_id = _mint_message_id(from_address_for(lead))
        msg.save()

        # The footer is applied at send time and never stored back onto the lead —
        # storing it would mean the next redraft appends a second one.
        wire_body = body + "\n" + compliance_footer(lead.email)
        # Per-lead CCs first, then the standing CC (marcus@). Dedupe case-insensitively
        # and never CC the recipient themselves.
        recipient = (lead.email or "").lower()
        cc_list: list[str] = []
        seen = {recipient}
        for addr in parse_cc(cc) + parse_cc(OUTREACH_CC):
            if addr.lower() not in seen:
                seen.add(addr.lower())
                cc_list.append(addr)
        # Anything already visible on CC must not also be BCC'd.
        bcc_list = [OUTREACH_BCC] if OUTREACH_BCC and OUTREACH_BCC.lower() not in seen else None
        message = EmailMessage(
            subject=subject.strip() or f"A note about {lead.organization or 'your work'}",
            body=wire_body,
            from_email=from_address_for(lead),
            to=[lead.email],
            cc=cc_list or None,
            bcc=bcc_list,
            # The exact ID stored on msg.message_id, set explicitly so Django does not
            # substitute its own (which anchors to the container hostname). This is
            # what an inbound reply's In-Reply-To/References will point back to.
            headers={"Message-ID": msg.message_id},
        )
        try:
            message.send(fail_silently=False)
        except Exception as exc:  # noqa: BLE001 — every failure must leave a record
            msg.status = OutreachMessage.Status.SEND_FAILED
            msg.send_error = _bounded_send_error(exc)
            msg.sent_at = None
            msg.save(update_fields=["status", "send_error", "sent_at", "updated_at"])
            send_exc = exc
        else:
            # Runs only on confirmed acceptance — there is no marked-sent-but-unsent path.
            msg.status = OutreachMessage.Status.SENT
            msg.sent_at = timezone.now()
            msg.send_error = ""  # a later success clears the stale failure text
            msg.save(update_fields=["status", "sent_at", "send_error", "updated_at"])
            lead.subject_line = subject.strip()[:255]
            lead.outreach_draft = body
            lead.cc_emails = ", ".join(cc_list)[:500]
            lead.email_status = "sent"
            # Through the outcome ladder, not an unconditional write: a reply
            # ingested between drafting and this send must not be erased by the
            # send's own bookkeeping. AWAITING applies only from blank/awaiting.
            from openoutreach.signals.models import OUTCOME_RANK
            if OUTCOME_RANK.get(lead.outreach_outcome, 0) < OUTCOME_RANK[SalesLead.Outcome.AWAITING]:
                lead.outreach_outcome = SalesLead.Outcome.AWAITING
            advance_to_contacted(lead)
            lead.updated_at = timezone.now()
            lead.save(update_fields=["subject_line", "outreach_draft", "cc_emails", "email_status",
                                     "outreach_outcome", "status", "updated_at"])
    if send_exc is not None:
        raise send_exc


