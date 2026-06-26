import logging

from django.conf import settings
from django.core.mail import send_mail

from openoutreach.signals.models import InterestSignup

logger = logging.getLogger(__name__)

ANANSI_ATLAS_SIGNUP_NOTIFICATION_RECIPIENT = "info@anansiatlas.com"


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
    try:
        send_mail(
            subject="You're on the Anansi Atlas waitlist",
            message=build_interest_signup_confirmation(signup),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[signup.email],
            fail_silently=False,
        )
    except Exception:
        logger.exception("Interest signup confirmation failed for signup_id=%s", signup.pk)
        return False
    return True
