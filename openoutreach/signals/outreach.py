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


OUTREACH_BCC = os.getenv("OUTREACH_BCC_EMAIL", "marcus@anansiatlas.com")
OUTREACH_WEBSITE = os.getenv("OUTREACH_WEBSITE", "anansiatlas.com")
OUTREACH_LINKEDIN = os.getenv("OUTREACH_LINKEDIN_URL", "linkedin.com/company/anansi-atlas")


def from_address_for(lead) -> str:
    """All outreach sends from the main sending mailbox (DEFAULT_FROM_EMAIL, mail@,
    DKIM-signed). Every send is BCC'd to marcus@ (a copy lands in Marcus's inbox)
    and Reply-To is marcus@ (replies come back there), so marcus@ is the single
    pane for the whole trail without being the send-from address. Env-override
    OUTREACH_FROM_EMAIL."""
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


def send_outreach_email(lead, subject: str, body: str, cc: str = "") -> None:
    """Send one outreach email to the lead (plus any CC), mark it sent, and
    advance its pipeline stage to Contacted. Sends from the main mailbox (see
    from_address_for), BCC'd to marcus@ so a copy lands in Marcus's inbox, with
    Reply-To (marcus@) stamped by the email backend so replies come back there
    too — the whole trail lives in one mailbox. Raises on SMTP failure so the
    caller can surface it — the lead is only marked sent on success.
    """
    cc_list = [a for a in parse_cc(cc) if a.lower() != (lead.email or "").lower()]
    bcc_list = [OUTREACH_BCC] if OUTREACH_BCC and OUTREACH_BCC.lower() != (lead.email or "").lower() else None
    message = EmailMessage(
        subject=subject.strip() or f"A note about {lead.organization or 'your work'}",
        body=body,
        from_email=from_address_for(lead),
        to=[lead.email],
        cc=cc_list or None,
        bcc=bcc_list,
    )
    message.send(fail_silently=False)
    lead.subject_line = subject.strip()[:255]
    lead.outreach_draft = body
    lead.cc_emails = ", ".join(cc_list)[:500]
    lead.email_status = "sent"
    lead.outreach_outcome = SalesLead.Outcome.AWAITING
    advance_to_contacted(lead)
    lead.updated_at = timezone.now()
    lead.save(update_fields=["subject_line", "outreach_draft", "cc_emails", "email_status",
                             "outreach_outcome", "status", "updated_at"])
