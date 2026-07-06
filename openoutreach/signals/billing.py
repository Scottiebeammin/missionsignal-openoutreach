"""
Stripe → account provisioning bridge.

A founding-seat purchase (Stripe payment link checkout) fires the
`checkout.session.completed` webhook here. We then:
  1. create the Django user (idempotent — an existing user is reused),
  2. mark any matching InterestSignup rows CONVERTED,
  3. email the buyer a password-set link that drops them into the client
     portal (login → /intake/ → their project portal), plus the scheduling
     link for the Founder Walkthrough when SCHEDULING_URL is configured,
  4. notify the operator.

Requires env vars on the web service:
  STRIPE_SECRET_KEY      — already set for the seat counter
  STRIPE_WEBHOOK_SECRET  — from the Stripe dashboard webhook endpoint
  SCHEDULING_URL         — optional Cal.com booking link (open-source scheduler)
"""

import logging
import os

import stripe
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.http import HttpResponse, HttpResponseBadRequest
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from openoutreach.core.access import founding_partners_group
from openoutreach.signals.models import InterestSignup, SalesLead
from openoutreach.signals.notifications import OPERATOR_RECIPIENTS

logger = logging.getLogger(__name__)

SITE_BASE_URL = "https://app.anansiatlas.com"


def _password_set_url(user) -> str:
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    path = reverse("password_reset_confirm", kwargs={"uidb64": uidb64, "token": token})
    return f"{SITE_BASE_URL}{path}"


def _provision_user(email: str, full_name: str):
    """Create (or fetch) the user for a paid founding seat. Returns (user, created)."""
    User = get_user_model()
    existing = User.objects.filter(email__iexact=email).first()
    if existing:
        return existing, False
    parts = full_name.split() if full_name else []
    user = User.objects.create_user(
        username=email.lower(),
        email=email.lower(),
        first_name=parts[0] if parts else "",
        last_name=" ".join(parts[1:]) if len(parts) > 1 else "",
    )
    user.set_unusable_password()
    user.save(update_fields=["password"])
    return user, True


def _send_seat_welcome(user, scheduling_url: str) -> bool:
    first_name = user.first_name or user.email.split("@")[0]
    set_password_url = _password_set_url(user)
    lines = [
        f"Hi {first_name},",
        "",
        "Your Founding Atlas Partner seat is confirmed — welcome to Anansi Atlas.",
        "",
        "Here's how to get into your client portal (takes about two minutes):",
        "",
        f"  1. Set your password: {set_password_url}",
        f"  2. Sign in at {SITE_BASE_URL}/accounts/login/",
        "  3. Complete the short organization intake — your Opportunity Web "
        "Snapshot starts building the moment you finish.",
        "",
        "Once you're in, here's a 3-minute tour of your dashboard so you know "
        f"where everything lives: {os.getenv('ONBOARDING_VIDEO_URL', 'https://youtu.be/AL7wfKWrlAk')}",
    ]
    if scheduling_url:
        lines += [
            "",
            "Then book your 45-minute Founder Walkthrough — pick any time that "
            f"works for you: {scheduling_url}",
        ]
    else:
        lines += [
            "",
            "I'll reach out within 24 hours to schedule your 45-minute Founder Walkthrough.",
        ]
    lines += [
        "",
        "Your founding rate — $150/month — is locked for life. Questions any time: "
        "just reply to this email.",
        "",
        "— Marcus Scott",
        "Anansi Atlas · Scott Foundry Group LLC",
        "info@anansiatlas.com",
    ]
    try:
        send_mail(
            subject="Your Anansi Atlas founding seat is confirmed — portal access inside",
            message="\n".join(lines),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception:
        logger.exception("Seat welcome email failed for user=%s", user.pk)
        return False
    return True


def _notify_operator_seat(email: str, full_name: str, user, created: bool, signups_converted: int):
    body = "\n".join([
        "New FOUNDING SEAT purchased via Stripe.",
        "",
        f"Buyer: {full_name or '(no name on checkout)'} <{email}>",
        f"Account: {'created' if created else 'already existed'} (user id {user.pk})",
        f"Waitlist signups marked converted: {signups_converted}",
        "",
        "The buyer received a password-set link and (if configured) the walkthrough "
        "scheduling link. Portal intake will notify you separately when they complete it.",
        "",
        f"Admin: {SITE_BASE_URL}/admin/auth/user/{user.pk}/change/",
    ])
    try:
        send_mail(
            subject=f"🎉 Founding seat purchased — {full_name or email}",
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=OPERATOR_RECIPIENTS,
            fail_silently=False,
        )
    except Exception:
        logger.exception("Operator seat notification failed for %s", email)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    if not webhook_secret:
        logger.error("STRIPE_WEBHOOK_SECRET not configured; rejecting webhook")
        return HttpResponse(status=503)
    try:
        event = stripe.Webhook.construct_event(
            request.body,
            request.META.get("HTTP_STRIPE_SIGNATURE", ""),
            webhook_secret,
        )
    except (ValueError, stripe.SignatureVerificationError):
        logger.warning("Stripe webhook signature verification failed")
        return HttpResponseBadRequest("invalid signature")

    if event["type"] != "checkout.session.completed":
        return HttpResponse(status=200)

    session = event["data"]["object"]
    details = session.get("customer_details") or {}
    email = (details.get("email") or session.get("customer_email") or "").strip()
    full_name = (details.get("name") or "").strip()
    if not email:
        logger.error("checkout.session.completed with no email; session=%s", session.get("id"))
        return HttpResponse(status=200)  # ack — nothing actionable, don't make Stripe retry

    user, created = _provision_user(email, full_name)
    user.groups.add(founding_partners_group())
    converted = InterestSignup.objects.filter(email__iexact=email).exclude(
        status=InterestSignup.Status.CONVERTED
    ).update(status=InterestSignup.Status.CONVERTED)
    # Close the loop in the sales pipeline: a purchase = Closed — Won.
    SalesLead.objects.filter(email__iexact=email).exclude(
        status=SalesLead.Status.CLOSED
    ).update(status=SalesLead.Status.CLOSED)

    from openoutreach.signals.notifications import scheduling_url as _scheduling_url
    _send_seat_welcome(user, _scheduling_url())
    _notify_operator_seat(email, full_name, user, created, converted)
    logger.info(
        "Provisioned founding seat: email=%s created=%s signups_converted=%s",
        email, created, converted,
    )
    return HttpResponse(status=200)
