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
