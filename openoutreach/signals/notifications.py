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
    try:
        send_mail(
            subject="New Anansi Atlas interest signup",
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
        "— Marcus Scott",
        "Founder, Anansi Atlas / Scott Foundry Group LLC",
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
    Notify the operator (Marcus) that a new org has completed intake.
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
