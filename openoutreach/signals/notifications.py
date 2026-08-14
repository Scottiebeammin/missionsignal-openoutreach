import logging
import os

from django.conf import settings
from django.core.mail import send_mail

from openoutreach.signals.models import InterestSignup

ANANSI_ATLAS_OPERATOR_EMAIL = "info@anansiatlas.com"
MARCUS_EMAIL = "marcus@anansiatlas.com"
# Operator alerts (new signups, questions, completed intakes) go to the shared
# inbox AND Marcus's personal inbox so nothing waits unseen.
OPERATOR_RECIPIENTS = [ANANSI_ATLAS_OPERATOR_EMAIL, MARCUS_EMAIL]


DEFAULT_SCHEDULING_URL = "https://cal.com/marcus-scott-br7maf/founder-walkthrough"


def scheduling_url() -> str:
    """Cal.com booking link for the Founder Walkthrough. Defaults to Marcus's
    live Cal link so every email offers self-serve booking; SCHEDULING_URL env
    overrides it. Set SCHEDULING_URL="" to suppress and use 'we'll reach out' copy."""
    return os.getenv("SCHEDULING_URL", DEFAULT_SCHEDULING_URL)

logger = logging.getLogger(__name__)


def form_confirmations_enabled() -> bool:
    """Auto-confirmations to public-form submitters are OFF by default.

    Bots beat the honeypot for 11 straight days (Aug 3-13, 2026) and the app
    dutifully confirmed every junk address they typed — 739 bounces that
    trashed the domain's sending reputation and pushed the outreach engine's
    mail into spam folders. Operator alerts still fire, so a human answers
    real people. Set ATLAS_FORM_CONFIRMATIONS_ENABLED=true only once real bot
    protection sits in front of the public forms.
    """
    return os.getenv("ATLAS_FORM_CONFIRMATIONS_ENABLED", "").strip().lower() == "true"


def build_interest_signup_notification(signup: InterestSignup) -> str:
    return "\n".join(
        [
            "New Anansi Atlas interest signup",
            "",
            f"Name: {signup.name}",
            f"Organization: {signup.organization}",
            f"Email: {signup.email}",
            f"Role / Title: {signup.role or 'Not provided'}",
            f"Website: {signup.website or 'Not provided'}",
            f"Interest Type: {signup.get_interest_type_display()}",
            f"Message: {signup.message or 'Not provided'}",
            f"Created At: {signup.created_at.isoformat()}",
        ]
    )


def notify_interest_signup(signup: InterestSignup) -> bool:
    is_question = signup.interest_type == InterestSignup.InterestType.QUESTION
    subject = (
        f"New question from {signup.name}"
        if is_question
        else "New Anansi Atlas interest signup"
    )
    try:
        send_mail(
            subject=subject,
            message=build_interest_signup_notification(signup),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=OPERATOR_RECIPIENTS,
            fail_silently=False,
        )
    except Exception:
        logger.exception("Interest signup notification failed for signup_id=%s", signup.pk)
        return False
    return True


def build_interest_signup_confirmation(signup: InterestSignup) -> str:
    first_name = signup.name.split()[0] if signup.name.strip() else "there"
    return "\n".join(
        [
            f"Hi {first_name},",
            "",
            "Thanks for joining the Anansi Atlas waitlist — we're glad you're here.",
            "",
            "Anansi Atlas maps the web of opportunity around your mission: aligned funders, "
            "strategic partners, government pathways, readiness gaps, and a 30-day action plan.",
            "",
            (
                "Book your onboarding call directly — pick any time that works for you: "
                f"{scheduling_url()}. Or if you'd rather wait, we'll follow up within 48 hours."
                if scheduling_url()
                else "We'll follow up within 48 hours to schedule your onboarding and "
                "Opportunity Web Snapshot walkthrough."
            )
            + " If you have questions in the meantime, just reply to this "
            "email or reach us at info@anansiatlas.com.",
            "",
            "— The Anansi Atlas Team",
            "Scott Foundry Group LLC",
        ]
    )


def send_interest_signup_confirmation(signup: InterestSignup) -> bool:
    if not form_confirmations_enabled():
        logger.info("Waitlist confirmation suppressed (disabled) for signup_id=%s", signup.pk)
        return False
    from openoutreach.signals.email_renderer import render_email
    first_name = signup.name.split()[0] if signup.name.strip() else "there"
    try:
        send_mail(
            subject="You're on the Anansi Atlas waitlist",
            message=build_interest_signup_confirmation(signup),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[signup.email],
            html_message=render_email("waitlist_confirmation.html", {
                "first_name": first_name,
                "org_name": signup.organization or "your organization",
            }),
            fail_silently=False,
        )
    except Exception:
        logger.exception("Interest signup confirmation failed for signup_id=%s", signup.pk)
        return False
    return True


def send_question_received_confirmation(signup: InterestSignup) -> bool:
    """Short confirmation to someone who submitted a question / info request."""
    if not form_confirmations_enabled():
        logger.info("Question confirmation suppressed (disabled) for signup_id=%s", signup.pk)
        return False
    first_name = signup.name.split()[0] if signup.name.strip() else "there"
    body = "\n".join(
        [
            f"Hi {first_name},",
            "",
            "Thanks for reaching out to Anansi Atlas — we've received your question "
            "and a team member will get back to you within 48 hours.",
            "",
            "In the meantime, you can reply directly to this email or reach us anytime "
            "at info@anansiatlas.com.",
            "",
            "— The Anansi Atlas Team",
            "Scott Foundry Group LLC",
        ]
    )
    try:
        send_mail(
            subject="We got your question — Anansi Atlas",
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[signup.email],
            fail_silently=False,
        )
    except Exception:
        logger.exception("Question confirmation failed for signup_id=%s", signup.pk)
        return False
    return True


def send_opportunity_alert(user, project, new_matches, deadline_items) -> bool:
    """Email a project owner: upcoming deadlines + newly-matched grants.

    `deadline_items` = list of (opportunity, days_until). `new_matches` = list of
    opportunities. Caller guarantees at least one is non-empty.
    """
    first = user.first_name or (user.email.split("@")[0] if user.email else "there")
    org = project.organization.name
    lines = [f"Hi {first},", "", f"Your Anansi Atlas update for {org}:", ""]

    if deadline_items:
        lines.append("UPCOMING DEADLINES")
        for opp, days in deadline_items:
            when = "today" if days == 0 else (f"in {days} day" + ("" if days == 1 else "s"))
            lines.append(f"  - {opp.name} - due {opp.deadline} ({when})")
            if opp.source_urls:
                lines.append(f"      {opp.source_urls[0]}")
        lines.append("")

    if new_matches:
        lines.append("NEW MATCHES FOUND")
        for opp in new_matches:
            due = f" - due {opp.deadline}" if opp.deadline else ""
            lines.append(f"  - {opp.name}{due}")
            if opp.source_urls:
                lines.append(f"      {opp.source_urls[0]}")
        lines.append("")

    lines += [
        f"See everything in your pipeline: https://anansiatlas.com/projects/{project.pk}/opportunities/",
        "",
        "— The Anansi Atlas Team",
        "info@anansiatlas.com",
    ]
    subject_bits = []
    if deadline_items:
        subject_bits.append(f"{len(deadline_items)} deadline" + ("" if len(deadline_items) == 1 else "s"))
    if new_matches:
        subject_bits.append(f"{len(new_matches)} new match" + ("" if len(new_matches) == 1 else "es"))
    try:
        send_mail(
            subject=f"{org}: {', '.join(subject_bits)}",
            message="\n".join(lines),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception:
        logger.exception("Opportunity alert failed for user=%s project=%s", user.pk, project.pk)
        return False
    return True


def send_website_drift_nudge(user, project, missing_items) -> bool:
    """Email a project owner when the monthly rescan finds profile claims that
    are no longer visible on their website. `missing_items` = list of dicts
    with 'claim' and 'kind'."""
    first = user.first_name or (user.email.split("@")[0] if user.email else "there")
    org = project.organization.name
    lines = [
        f"Hi {first},",
        "",
        f"During this month's website check for {org}, a few things in your Anansi Atlas "
        "profile weren't visible on your website. Funders often check your site, so it "
        "helps when the two line up:",
        "",
    ]
    for item in missing_items:
        lines.append(f"  - {item['claim']} ({item['kind']})")
    lines += [
        "",
        "Either add these to your website, or adjust your profile in Settings — your call.",
        f"Review it here: https://anansiatlas.com/projects/{project.pk}/analysis/",
        "",
        "— The Anansi Atlas Team",
        "info@anansiatlas.com",
    ]
    try:
        send_mail(
            subject=f"{org}: {len(missing_items)} profile item"
                    + ("" if len(missing_items) == 1 else "s")
                    + " not visible on your website",
            message="\n".join(lines),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception:
        logger.exception("Website drift nudge failed for user=%s project=%s", user.pk, project.pk)
        return False
    return True


def send_interest_reminder(user, project, tracked_items) -> bool:
    """Weekly reminder of the opportunities the org is TRACKING (interested, not yet
    applied). `tracked_items` = list of (opportunity, days_until_deadline_or_None)."""
    first = user.first_name or (user.email.split("@")[0] if user.email else "there")
    org = project.organization.name
    n = len(tracked_items)
    lines = [
        f"Hi {first},",
        "",
        f"You're tracking {n} opportunit" + ("y" if n == 1 else "ies") + f" for {org}. "
        "Here's your weekly reminder — apply, or un-track any you've decided to skip:",
        "",
    ]
    for opp, days in tracked_items:
        if opp.deadline and days is not None:
            when = "today" if days == 0 else (
                f"{days} day" + ("" if days == 1 else "s") + " left" if days > 0 else "deadline passed"
            )
            lines.append(f"  - {opp.name} - due {opp.deadline} ({when})")
        else:
            lines.append(f"  - {opp.name} - rolling / no fixed deadline")
        if opp.source_urls:
            lines.append(f"      {opp.source_urls[0]}")
    lines += [
        "",
        f"Manage them in your pipeline: https://anansiatlas.com/projects/{project.pk}/opportunities/",
        "(Reminders stop automatically once you mark one applied or un-track it.)",
        "",
        "— The Anansi Atlas Team",
        "info@anansiatlas.com",
    ]
    try:
        send_mail(
            subject=f"{org}: {n} tracked opportunit" + ("y" if n == 1 else "ies") + " — weekly reminder",
            message="\n".join(lines),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception:
        logger.exception("Interest reminder failed for user=%s project=%s", user.pk, project.pk)
        return False
    return True


# ── Intake welcome emails ─────────────────────────────────────────────────────

def send_intake_welcome(user, project) -> bool:
    """
    Send a welcome email to the new founding partner after they complete intake.
    """
    first_name = user.first_name or user.email.split("@")[0]
    org_name = project.organization.name
    snapshot_url = f"{settings.SITE_BASE_URL}/projects/{project.pk}/snapshot/"
    body = "\n".join([
        f"Hi {first_name},",
        "",
        f"Welcome to Anansi Atlas — {org_name} is now part of our founding cohort.",
        "",
        "Your Opportunity Web Snapshot is ready. It maps the funders, partners, and "
        "pathways most aligned with your mission, along with a 30-day action plan and "
        "readiness score specific to your organization.",
        "",
        f"View your Snapshot: {snapshot_url}",
        "",
        "What's happening behind the scenes:",
        "  1. Your intake has been received and your organization profile is built.",
        "  2. Anansi Atlas has run a deterministic analysis of your mission, "
        "focus areas, and geography.",
        "  3. Our AI research engine is now identifying real, verifiable funders and "
        "opportunities aligned to your work. This may take a few minutes.",
        "",
        (
            "Book your Founder Walkthrough now — a 45-minute call where we'll walk "
            f"through your Snapshot together and build your first action plan: {scheduling_url()}"
            if scheduling_url()
            else "I'll reach out personally within 24 hours to schedule your Founder "
            "Walkthrough — a 45-minute call where we'll walk through your Snapshot "
            "together and build your first action plan."
        ),
        "",
        "If you have questions before then, just reply here.",
        "",
        "— The Anansi Atlas Team",
        "info@anansiatlas.com",
    ])
    from openoutreach.signals.email_renderer import render_email
    snapshot_url = f"{settings.SITE_BASE_URL}/projects/{project.pk}/snapshot/"
    try:
        send_mail(
            subject=f"Welcome to Anansi Atlas — your Snapshot is ready, {first_name}",
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=render_email("intake_welcome.html", {
                "first_name": first_name,
                "org_name": org_name,
                "snapshot_url": snapshot_url,
            }),
            fail_silently=False,
        )
    except Exception:
        logger.exception("Intake welcome email failed for user=%s project=%s", user.pk, project.pk)
        return False
    return True


def notify_new_intake(user, project) -> bool:
    """
    Notify the operator that a new org has completed intake.
    """
    org = project.organization
    body = "\n".join([
        "New Anansi Atlas intake completed.",
        "",
        f"Organization: {org.name}",
        f"User: {user.get_full_name() or user.username} <{user.email}>",
        f"Mission: {org.mission or 'Not provided'}",
        f"Geography: {org.geography or 'Not provided'}",
        f"Focus Areas: {org.focus_areas or 'Not provided'}",
        f"Project ID: {project.pk}",
        "",
        f"Admin: {settings.SITE_BASE_URL}/admin/core/project/{project.pk}/change/",
        f"Operator: {settings.SITE_BASE_URL}/operator/organizations/{project.pk}/",
    ])
    try:
        send_mail(
            subject=f"New intake: {org.name}",
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=OPERATOR_RECIPIENTS,
            fail_silently=False,
        )
    except Exception:
        logger.exception("Operator intake notification failed for project=%s", project.pk)
        return False
    return True


WHO_WE_ARE_VIDEO = "https://youtu.be/FBvLg9c35Qo"  # "WhoWeAre & Walkthrough" explainer


def build_who_we_are_email(first_name: str, org_name: str) -> str:
    """The 'who we are & walkthrough' email — the explainer touch with the
    WhoWeAre video. Companion to the seat-welcome (which carries the join links
    + the dashboard walkthrough). Warm outreach, so it sends from marcus@."""
    video = os.getenv("WHO_WE_ARE_VIDEO_URL", WHO_WE_ARE_VIDEO)
    return "\n".join([
        f"Hi {first_name or 'there'},",
        "",
        "Now that you're set up, I wanted to share the story behind what you're "
        "stepping into — who we are and how Anansi Atlas actually works.",
        "",
        "Every mission has an opportunity ecosystem around it: aligned funders, "
        "strategic partners, government pathways, and free resources. Most of it "
        "stays invisible because no one has time to map it. Anansi Atlas maps it "
        f"for you — for {org_name}, that's your funders, partners, and pathways in "
        "one clear picture, with a readiness read and a 30-day plan.",
        "",
        f"Here's a 3-minute look at who we are and how it works: {video}",
        "",
        "You can jump into your workspace any time, and I'd genuinely love to walk "
        "it through with you live whenever works — just reply and we'll find a time.",
        "",
        "So glad to have you as a founding partner.",
        "",
        "— Marcus Scott",
        "Founder, Anansi Atlas · The Web of Opportunity",
    ])


def send_who_we_are_email(user, project) -> bool:
    """Send the who-we-are & walkthrough email to a client. Warm → from marcus@."""
    org = project.organization
    first = user.first_name or (user.email.split("@")[0] if user.email else "there")
    from django.core.mail import EmailMessage
    msg = EmailMessage(
        subject=f"Who we are — the story behind Anansi Atlas, for {org.name}",
        body=build_who_we_are_email(first, org.name),
        from_email=os.getenv("WARM_FROM_EMAIL", MARCUS_EMAIL),
        to=[user.email],
    )
    try:
        msg.send(fail_silently=False)
    except Exception:
        logger.exception("Who-we-are email failed for user=%s", user.pk)
        return False
    return True
