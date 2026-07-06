"""
Server-side outreach composer + send helper for the operator cockpit.

Deterministic draft generation (no LLM required) so the outreach queue always
has a solid starting email the operator can edit before sending. Mirrors the
retired n8n composer's warm/cold template — sales walkthrough video, offer, and
a soft CTA — but lives on the server so review-edit-send happens in one place.
"""
import os
import re

from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone

from openoutreach.signals.models import SalesLead

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
        "annual": os.getenv("STRIPE_ANNUAL_URL", ""),
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
        angle = f"\n\n{lead.focus_area.strip()}" if lead.focus_area else ""
    else:
        if lead.why_fit:
            reason = lead.why_fit.strip()
        elif lead.focus_area:
            reason = (f"{org}'s work in {lead.focus_area.strip()} is exactly the kind of "
                      "mission our funder map is built around")
        else:
            reason = f"{org} is exactly the kind of Central Florida nonprofit our funder map is built for"
        opening = (
            f"Hi {first},\n\nI'm Marcus Scott, founder of Anansi Atlas here in Central Florida. "
            f"I'm reaching out because {reason}."
        )
        angle = ""  # the cold hook is folded into the opening reason

    lines = [
        f"{opening}{angle}",
        "",
        "I've built Anansi Atlas: it maps the web of opportunity around a nonprofit's "
        "mission — aligned funders, partners, government pathways, and free capacity-"
        "building resources — into one clear brief with a readiness read and a 30-day "
        "action plan.",
        "",
        "Here's a 3-minute look at the actual platform (no pitch deck, the real thing):",
        links["video"],
        "",
    ]
    offer = f"If it clicks, you can claim a founding seat ($150/mo, locked for life): {links['signup']}"
    if links["annual"]:
        offer += f"\nAnnual option ($1,440/yr — save 20%): {links['annual']}"
    lines.append(offer)
    if links["cal"]:
        lines.append(f"Or grab 45 minutes with me first: {links['cal']}")
    lines += [
        "",
        f"Either way — glad {org} is out there doing this work.",
        "",
        "— Marcus",
        "Anansi Atlas · The Web of Opportunity · anansiatlas.com",
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


def from_address_for(lead) -> str:
    """All outreach — warm, cold, and call follow-ups — sends from Marcus's
    address, so every thread lives in one mailbox: sent copies in marcus@'s Sent
    folder (when SMTP authenticates as marcus@) and replies in marcus@'s inbox
    (via the Reply-To the backend stamps). @anansiatlas.com, so DKIM-signed.
    Env-override OUTREACH_FROM_EMAIL."""
    return os.getenv("OUTREACH_FROM_EMAIL", os.getenv("WARM_FROM_EMAIL", "marcus@anansiatlas.com"))


def parse_cc(cc_emails: str) -> list[str]:
    """Split a comma/semicolon/space-separated CC string into clean addresses."""
    parts = re.split(r"[,;\s]+", (cc_emails or "").strip())
    return [p for p in (x.strip() for x in parts) if "@" in p]


def send_outreach_email(lead, subject: str, body: str, cc: str = "") -> None:
    """Send one outreach email to the lead (plus any CC) and mark it sent. All
    outreach sends from marcus@ (see from_address_for) and Reply-To (marcus@) is
    stamped by the email backend, so the whole trail lives in one mailbox. Raises
    on SMTP failure so the caller can surface it — the lead is only marked sent on
    success.
    """
    cc_list = [a for a in parse_cc(cc) if a.lower() != (lead.email or "").lower()]
    message = EmailMessage(
        subject=subject.strip() or f"A note about {lead.organization or 'your work'}",
        body=body,
        from_email=from_address_for(lead),
        to=[lead.email],
        cc=cc_list or None,
    )
    message.send(fail_silently=False)
    lead.subject_line = subject.strip()[:255]
    lead.outreach_draft = body
    lead.cc_emails = ", ".join(cc_list)[:500]
    lead.email_status = "sent"
    lead.updated_at = timezone.now()
    lead.save(update_fields=["subject_line", "outreach_draft", "cc_emails", "email_status", "updated_at"])
