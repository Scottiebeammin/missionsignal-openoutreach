"""
Server-side outreach composer + send helper for the operator cockpit.

Deterministic draft generation (no LLM required) so the outreach queue always
has a solid starting email the operator can edit before sending. Mirrors the
retired n8n composer's warm/cold template — sales walkthrough video, offer, and
a soft CTA — but lives on the server so review-edit-send happens in one place.
"""
import os

from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone

from openoutreach.signals.models import SalesLead

_WARMTH_RANK = {"hot": 0, "warm": 1, "reconnect": 2, "cold": 3}


def outreach_queue():
    """Leads still to email, hottest first (warm segment, then warmth, then org)."""
    leads = list(SalesLead.objects.filter(email_status="not_sent").exclude(email=""))
    leads.sort(key=lambda l: (
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


def compose_outreach_email(lead) -> tuple[str, str]:
    """Return (subject, body) for a lead — the editable starting draft."""
    first = (lead.name or "").split(" ")[0] or "there"
    org = lead.organization or "your organization"
    warm = lead.list_segment == "warm"
    links = _links()

    if warm:
        opening = (
            f"Hi {first},\n\nIt's Marcus — {lead.why_fit.strip()}."
            if lead.why_fit else
            f"Hi {first},\n\nIt's Marcus — it's been a minute."
        )
    else:
        reason = lead.why_fit.strip() if lead.why_fit else f"{org} sits right in the middle of the work we map"
        opening = (
            f"Hi {first},\n\nI'm Marcus Scott, founder of Anansi Atlas here in Central Florida. "
            f"I'm reaching out because {reason}."
        )

    angle = f"\n\n{lead.focus_area.strip()}" if lead.focus_area else ""

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


def send_outreach_email(lead, subject: str, body: str) -> None:
    """Send one outreach email from the platform sender to the lead, and mark it
    sent. Reply-To (marcus@) is stamped by the email backend. Raises on SMTP
    failure so the caller can surface it — the lead is only marked sent on success.
    """
    message = EmailMessage(
        subject=subject.strip() or f"A note about {lead.organization or 'your work'}",
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[lead.email],
    )
    message.send(fail_silently=False)
    lead.subject_line = subject.strip()[:255]
    lead.outreach_draft = body
    lead.email_status = "sent"
    lead.updated_at = timezone.now()
    lead.save(update_fields=["subject_line", "outreach_draft", "email_status", "updated_at"])
