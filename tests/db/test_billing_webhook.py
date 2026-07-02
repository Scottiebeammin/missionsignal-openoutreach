"""Stripe checkout webhook → auto account provisioning (openoutreach/signals/billing.py)."""

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from openoutreach.signals.models import InterestSignup

pytestmark = pytest.mark.django_db

WEBHOOK_PATH = "/billing/stripe-webhook/"


def _checkout_event(email="buyer@nonprofit.org", name="Jordan Rivera"):
    return {
        "type": "checkout.session.completed",
        "data": {"object": {
            "id": "cs_test_123",
            "customer_details": {"email": email, "name": name},
        }},
    }


def _post_webhook(event):
    with patch.dict("os.environ", {"STRIPE_WEBHOOK_SECRET": "whsec_test"}), \
         patch("openoutreach.signals.billing.stripe.Webhook.construct_event", return_value=event):
        return Client().post(WEBHOOK_PATH, data=b"{}", content_type="application/json",
                             HTTP_STRIPE_SIGNATURE="sig")


def test_checkout_provisions_user_and_converts_signup(mailoutbox):
    signup = InterestSignup.objects.create(
        name="Jordan Rivera", organization="Riverside Girls Collective",
        email="buyer@nonprofit.org",
        interest_type=InterestSignup.InterestType.FOUNDING_ATLAS_PARTNERS,
    )
    resp = _post_webhook(_checkout_event())
    assert resp.status_code == 200

    user = get_user_model().objects.get(email="buyer@nonprofit.org")
    assert user.first_name == "Jordan"
    assert not user.has_usable_password()

    signup.refresh_from_db()
    assert signup.status == InterestSignup.Status.CONVERTED

    # welcome (password-set link) + operator notification
    assert len(mailoutbox) == 2
    welcome = next(m for m in mailoutbox if m.to == ["buyer@nonprofit.org"])
    assert "/accounts/reset/" in welcome.body
    operator = next(m for m in mailoutbox if m.to == ["info@anansiatlas.com"])
    assert "FOUNDING SEAT" in operator.body


def test_checkout_is_idempotent_for_existing_user(mailoutbox):
    get_user_model().objects.create_user(username="buyer@nonprofit.org", email="buyer@nonprofit.org")
    resp = _post_webhook(_checkout_event())
    assert resp.status_code == 200
    assert get_user_model().objects.filter(email__iexact="buyer@nonprofit.org").count() == 1


def test_scheduling_link_included_when_configured(mailoutbox):
    with patch.dict("os.environ", {"SCHEDULING_URL": "https://cal.com/marcus-scott/walkthrough"}):
        resp = _post_webhook(_checkout_event())
    assert resp.status_code == 200
    welcome = next(m for m in mailoutbox if m.to == ["buyer@nonprofit.org"])
    assert "cal.com/marcus-scott/walkthrough" in welcome.body


def test_bad_signature_rejected():
    with patch.dict("os.environ", {"STRIPE_WEBHOOK_SECRET": "whsec_test"}), \
         patch("openoutreach.signals.billing.stripe.Webhook.construct_event", side_effect=ValueError):
        resp = Client().post(WEBHOOK_PATH, data=b"{}", content_type="application/json",
                             HTTP_STRIPE_SIGNATURE="bad")
    assert resp.status_code == 400


def test_missing_secret_returns_503():
    with patch.dict("os.environ", {"STRIPE_WEBHOOK_SECRET": ""}):
        resp = Client().post(WEBHOOK_PATH, data=b"{}", content_type="application/json")
    assert resp.status_code == 503


def test_purchase_closes_matching_sales_lead(mailoutbox):
    from openoutreach.signals.models import SalesLead
    lead = SalesLead.objects.create(
        name="Jordan Rivera", email="buyer@nonprofit.org",
        source=SalesLead.Source.WARM, status=SalesLead.Status.CALL_DONE,
    )
    resp = _post_webhook(_checkout_event())
    assert resp.status_code == 200
    lead.refresh_from_db()
    assert lead.status == SalesLead.Status.CLOSED
