"""
Waitlist nurture email sequence for Anansi Atlas.

Three emails anchored to signup.created_at:
  Step 1 — 1 day  after signup: "Here's what you'll see inside"
  Step 2 — 3 days after signup: "A real example of the Opportunity Web"
  Step 3 — 7 days after signup: "Your spot is still here — a personal note"

Public API:
  send_due_nurture_emails(now, dry_run=False) -> (sent, skipped)
"""
from __future__ import annotations

import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from openoutreach.signals.models import InterestSignup

logger = logging.getLogger(__name__)

# Days after signup when each step fires
_STEP_DAYS = {1: 1, 2: 3, 3: 7}

# Total steps in the sequence
_MAX_STEP = 3


def send_due_nurture_emails(now=None, dry_run: bool = False) -> tuple[int, int]:
    """
    Send any nurture emails that are due.

    Returns (sent_count, skipped_count).
    """
    if now is None:
        now = timezone.now()

    signups = InterestSignup.objects.filter(
        nurture_step__lt=_MAX_STEP,
        status__in=[InterestSignup.Status.NEW, InterestSignup.Status.REVIEWED],
    )

    sent = 0
    skipped = 0

    for signup in signups:
        next_step = signup.nurture_step + 1
        days_needed = _STEP_DAYS[next_step]
        due_at = signup.created_at + timedelta(days=days_needed)

        if now < due_at:
            skipped += 1
            continue

        subject, body = _build_email(signup, next_step)

        if dry_run:
            logger.info("[DRY RUN] Would send step %s to %s", next_step, signup.email)
            sent += 1
            continue

        try:
            from openoutreach.signals.email_renderer import render_email
            first_name = signup.name.split()[0] if signup.name.strip() else "there"
            html = render_email(f"nurture_{next_step}.html", {
                "first_name": first_name,
                "org_name": signup.organization or "your organization",
            })
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[signup.email],
                html_message=html,
                fail_silently=False,
            )
            signup.nurture_step = next_step
            signup.save(update_fields=["nurture_step"])
            sent += 1
            logger.info("Nurture step %s sent to %s", next_step, signup.email)
        except Exception:
            logger.exception("Nurture email failed for signup=%s step=%s", signup.pk, next_step)
            skipped += 1

    return sent, skipped


def _build_email(signup: InterestSignup, step: int) -> tuple[str, str]:
    first_name = signup.name.split()[0] if signup.name.strip() else "there"
    org = signup.organization or "your organization"

    if step == 1:
        return _step_1(first_name, org)
    if step == 2:
        return _step_2(first_name, org)
    return _step_3(first_name, org)


def _step_1(first_name: str, org: str) -> tuple[str, str]:
    subject = f"{first_name}, here's what you'll see inside Anansi Atlas"
    body = "\n".join([
        f"Hi {first_name},",
        "",
        "Thanks again for joining the Anansi Atlas waitlist.",
        "",
        "I wanted to give you a quick preview of what your Opportunity Web Snapshot "
        "actually looks like — because I think it's easier to understand the platform "
        "once you see it.",
        "",
        "Your Snapshot includes:",
        "",
        "  • A mission overview written specifically for your organization",
        "  • Your top funder archetypes — community foundations, corporate funders, "
        "federal agencies — ranked by alignment to your mission and geography",
        "  • Strategic partners already doing adjacent work you could collaborate with",
        "  • Active grant opportunities with deadlines, eligibility notes, and fit scores",
        "  • A 30-day action plan with prioritized steps",
        "  • A Readiness Score that shows funders where you stand — and what to strengthen",
        "",
        "For a workforce development org in the Southeast, this might surface a community "
        "foundation with a digital equity focus, a local workforce board partnership, and "
        "two federal grants with upcoming deadlines. For a youth arts nonprofit in Chicago, "
        "it looks completely different.",
        "",
        "That specificity is what makes it useful.",
        "",
        "If you have questions, just reply. I read every email.",
        "",
        "— The Anansi Atlas Team",
        "info@anansiatlas.com",
    ])
    return subject, body


def _step_2(first_name: str, org: str) -> tuple[str, str]:
    subject = "What the Opportunity Web looks like for a real nonprofit"
    body = "\n".join([
        f"Hi {first_name},",
        "",
        "I promised a real example — here's one.",
        "",
        "Empowered Girls Inc. is a workforce development nonprofit focused on young women "
        "of color in the Southeast. When we ran their Opportunity Web Snapshot, the platform "
        "surfaced:",
        "",
        "  • 8 funder archetypes — led by community foundations and federal workforce agencies",
        "  • 14 strategic partners — including community colleges, workforce boards, and "
        "corporate partners with internship pipelines",
        "  • 45 grant opportunities — 12 marked high priority, 6 with deadlines inside 90 days",
        "  • A Readiness Score of 68/100 — strong mission clarity, gap in documented outcomes",
        "  • A 30-day action plan starting with two grant applications and a workforce board meeting",
        "",
        "The platform didn't just show them a list. It showed them *why* each funder aligns, "
        "what to prepare before applying, and what risks to watch.",
        "",
        f"Your Snapshot for {org} would be built the same way — mapped to your specific "
        "mission, geography, and focus areas.",
        "",
        "We have 19 founding partner seats remaining. If you're ready to move, reply to this "
        "email and we'll get you set up.",
        "",
        "— The Anansi Atlas Team",
        "info@anansiatlas.com",
    ])
    return subject, body


def _step_3(first_name: str, org: str) -> tuple[str, str]:
    subject = f"Your spot is still here, {first_name}"
    body = "\n".join([
        f"Hi {first_name},",
        "",
        "I'll keep this short.",
        "",
        f"You signed up for the Anansi Atlas waitlist a week ago. Your spot is still open.",
        "",
        "Founding partner pricing is $150/month — locked for life. It includes your "
        "Opportunity Web Snapshot, full platform access as we build, a personal founder "
        "walkthrough, and a direct line to me.",
        "",
        "After the founding cohort fills (19 seats remaining), pricing goes up and "
        "the walkthrough goes away.",
        "",
        "If now isn't the right time, no pressure — I'll stop sending follow-ups after this. "
        "But if you want to talk through whether it's the right fit, just reply.",
        "",
        "— The Anansi Atlas Team",
        "info@anansiatlas.com",
        "",
        "P.S. If you've already signed up or decided it's not for you, just reply "
        "with 'unsubscribe' and I'll take you off the list.",
    ])
    return subject, body
