import logging

from django.conf import settings
from django.core.mail import send_mail

from openoutreach.signals.models import InterestSignup

ANANSI_ATLAS_OPERATOR_EMAIL = "info@anansiatlas.com"

logger = logging.getLogger(__name__)

ANANSI_ATLAS_SIGNUP_NOTIFICATION_RECIPIENT = ANANSI_ATLAS_OPERATOR_EMAIL


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
            recipient_list=[ANANSI_ATLAS_SIGNUP_NOTIFICATION_RECIPIENT],
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
            "We'll follow up within 48 hours to schedule your onboarding and Opportunity Web "
            "Snapshot walkthrough. If you have questions in the meantime, just reply to this "
            "email or reach us at info@anansiatlas.com.",
            "",
            "— The Anansi Atlas Team",
            "Scott Foundry Group LLC",
        ]
    )


def send_interest_signup_confirmation(signup: InterestSignup) -> bool:
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
    snapshot_url = f"https://app.anansiatlas.com/projects/{project.pk}/snapshot/"
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
        "I'll reach out personally within 24 hours to schedule your Founder Walkthrough "
        "— a 45-minute call where we'll walk through your Snapshot together and build "
        "your first action plan.",
        "",
        "If you have questions before then, just reply here.",
        "",
        "— The Anansi Atlas Team",
        "info@anansiatlas.com",
    ])
    from openoutreach.signals.email_renderer import render_email
    snapshot_url = f"https://app.anansiatlas.com/projects/{project.pk}/snapshot/"
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
        f"Admin: https://app.anansiatlas.com/admin/core/project/{project.pk}/change/",
        f"Operator: https://app.anansiatlas.com/operator/organizations/{project.pk}/",
    ])
    try:
        send_mail(
            subject=f"New intake: {org.name}",
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[ANANSI_ATLAS_OPERATOR_EMAIL],
            fail_silently=False,
        )
    except Exception:
        logger.exception("Operator intake notification failed for project=%s", project.pk)
        return False
    return True
