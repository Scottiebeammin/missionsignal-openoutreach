"""
Waitlist nurture email sequence for Anansi Atlas.

Three emails anchored to signup.created_at:
  Step 1 — 1 day  after signup: "Here's what you'll see inside"
  Step 2 — 3 days after signup: "A real example of the Opportunity Web"
  Step 3 — 7 days after signup: "Your spot is still here — a personal note"

This path is governed, because it is the one that can mail thousands of rows in a
single pass. Four gates, all enforced here because this is the only function that
mails a signup:

  1. ``EmailOptOut``      — the same suppression list ``send_outreach_email`` honours.
  2. ``_MAX_AGE_DAYS``    — a signup that has aged out is retired unsent, so a queue
                            that sat still for weeks can never discharge itself at
                            once when mail starts working.
  3. ``NURTURE_DAILY_LIMIT`` — a per-run ceiling on *attempted* sends.
  4. ``OUTREACH_MAILING_ADDRESS`` — no CAN-SPAM address, no send (matches outreach).

Every message carries a real unsubscribe: the compliance footer in the body and
RFC 8058 ``List-Unsubscribe`` headers, so gate 1 has a way to be populated.

Public API:
  send_due_nurture_emails(now, dry_run=False) -> NurtureRun
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

from openoutreach.signals.models import InterestSignup, SalesLead

logger = logging.getLogger(__name__)

# Days after signup when each step fires
_STEP_DAYS = {1: 1, 2: 3, 3: 7}

# Total steps in the sequence
MAX_STEP = 3

#: A signup this old never enters the sequence — it is retired unsent instead.
#: The sequence is a 7-day arc; mailing "you signed up a week ago" to someone who
#: signed up two months ago is wrong on its own terms. It is also the structural
#: answer to a queue that accumulated while sending was broken: without it, the
#: first run after mail is fixed discharges the whole backlog.
_MAX_AGE_DAYS = 30

#: Default ceiling on attempted sends per run. Deliberately low: this domain is
#: being reputation-warmed, and an uncapped pass over the waitlist is exactly the
#: shape of the bounce storm that burned it once already.
_DEFAULT_DAILY_LIMIT = 50


def _daily_limit() -> int:
    return int(os.getenv("NURTURE_DAILY_LIMIT", str(_DEFAULT_DAILY_LIMIT)))


@dataclass
class NurtureRun:
    """The outcome of one pass, with failures counted separately from non-events.

    The distinction is the whole point. The previous version folded "send raised"
    into the same counter as "not due yet" and returned 0, so a cron that failed
    every single send for a month was indistinguishable from a quiet one and
    Render reported success daily.
    """

    sent: int = 0
    skipped: int = 0      # not due yet — normal, expected, uninteresting
    suppressed: int = 0   # opted out or aged out — deliberately never sent
    failed: int = 0       # the send raised
    capped: int = 0       # due, but the daily limit was already reached

    @property
    def attempted(self) -> int:
        return self.sent + self.failed

    @property
    def total_failure(self) -> bool:
        """Every send this run raised. The signature of a broken transport rather
        than a bad address, and the condition the command exits non-zero on."""
        return self.failed > 0 and self.sent == 0


def _ensure_pipeline_lead(signup: InterestSignup) -> None:
    """A signup that finished the nurture sequence without converting becomes a
    SalesLead (Inbound / Nurturing) so it stays visible in the pipeline instead
    of dying quietly in the waitlist table. Idempotent by email."""
    if SalesLead.objects.filter(email__iexact=signup.email).exists():
        return
    SalesLead.objects.create(
        name=signup.name or signup.organization,
        organization=signup.organization,
        email=signup.email,
        role=signup.role[:200],
        source=SalesLead.Source.INBOUND,
        status=SalesLead.Status.NURTURING,
        notes=(
            "Auto-added: completed the 3-step waitlist nurture sequence without "
            f"converting. Interest: {signup.get_interest_type_display()}."
            + (f"\nSignup message: {signup.message}" if signup.message else "")
        ),
    )
    logger.info("SalesLead created from nurtured signup %s", signup.email)


def retire(signup: InterestSignup, reason: str) -> None:
    """Take a signup out of the sequence without mailing it.

    Marks the sequence complete so the row is not re-examined every day, and
    deliberately does NOT create a SalesLead — a retired signup did not complete
    the sequence, it was excluded from it, and a bot address must never land in
    the pipeline as an inbound lead.
    """
    signup.nurture_step = MAX_STEP
    signup.save(update_fields=["nurture_step"])
    logger.info("Nurture retired signup=%s (%s)", signup.pk, reason)


def _send_step(signup: InterestSignup, step: int) -> None:
    """Mail one step. Raises on failure — the caller counts it."""
    from openoutreach.signals.email_renderer import render_email
    from openoutreach.signals.outreach import compliance_footer
    from openoutreach.signals.unsubscribe import list_unsubscribe_headers

    subject, body = _build_email(signup, step)
    first_name = signup.name.split()[0] if signup.name.strip() else "there"
    html = render_email(f"nurture_{step}.html", {
        "first_name": first_name,
        "org_name": signup.organization or "your organization",
    })
    message = EmailMultiAlternatives(
        subject=subject,
        body=body + compliance_footer(signup.email),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[signup.email],
        headers=list_unsubscribe_headers(signup.email),
    )
    message.attach_alternative(html, "text/html")
    message.send(fail_silently=False)


def send_due_nurture_emails(now=None, dry_run: bool = False) -> NurtureRun:
    """Send any nurture emails that are due, subject to the four gates above."""
    from openoutreach.signals.outreach import OUTREACH_MAILING_ADDRESS
    from openoutreach.signals.unsubscribe import is_opted_out

    if now is None:
        now = timezone.now()

    run = NurtureRun()
    limit = _daily_limit()
    age_cutoff = now - timedelta(days=_MAX_AGE_DAYS)

    signups = InterestSignup.objects.filter(
        nurture_step__lt=MAX_STEP,
        status__in=[InterestSignup.Status.NEW, InterestSignup.Status.REVIEWED],
    ).order_by("created_at")

    for signup in signups.iterator(chunk_size=500):
        next_step = signup.nurture_step + 1
        due_at = signup.created_at + timedelta(days=_STEP_DAYS[next_step])

        if now < due_at:
            run.skipped += 1
            continue

        if signup.created_at < age_cutoff:
            run.suppressed += 1
            if not dry_run:
                retire(signup, "aged out")
            continue

        if is_opted_out(signup.email):
            run.suppressed += 1
            if not dry_run:
                retire(signup, "opted out")
            continue

        if run.attempted >= limit:
            run.capped += 1
            continue

        # Checked here rather than up front so a run with nothing due stays quiet:
        # the refusal should fire when a message would actually have gone out.
        if not OUTREACH_MAILING_ADDRESS:
            raise RuntimeError(
                f"{signup.email} is due nurture step {next_step}, but "
                "OUTREACH_MAILING_ADDRESS is unset — refusing to send a commercial "
                "email without the CAN-SPAM postal address. Set it in the Render "
                "environment for this service."
            )

        if dry_run:
            logger.info("[DRY RUN] Would send step %s to %s", next_step, signup.email)
            run.sent += 1
            continue

        try:
            _send_step(signup, next_step)
        except Exception:
            logger.exception("Nurture email failed for signup=%s step=%s", signup.pk, next_step)
            run.failed += 1
            continue

        signup.nurture_step = next_step
        signup.save(update_fields=["nurture_step"])
        run.sent += 1
        logger.info("Nurture step %s sent to %s", next_step, signup.email)
        if next_step == MAX_STEP:
            _ensure_pipeline_lead(signup)

    return run


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
