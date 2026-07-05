"""Open signup + activation paywall (core/access.py, core/views.py signup/portal/activate)."""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from openoutreach.core.access import founding_partners_group

pytestmark = pytest.mark.django_db

SIGNUP = {
    "first_name": "Rae", "last_name": "Kim", "email": "rae@neworg.org",
    "password1": "web-of-opportunity-7", "password2": "web-of-opportunity-7",
}


def test_signup_creates_account_and_routes_to_paywall():
    c = Client()
    r = c.post("/accounts/signup/", SIGNUP, HTTP_HOST="localhost", follow=True)
    assert r.redirect_chain[-1][0].endswith("/activate/")
    body = r.content.decode()
    assert "Claim your founding seat" in body
    assert "buy.stripe.com" in body
    assert "Message support" in body
    assert get_user_model().objects.filter(email="rae@neworg.org").exists()


def test_paid_user_passes_paywall_to_intake():
    c = Client()
    c.post("/accounts/signup/", SIGNUP, HTTP_HOST="localhost")
    user = get_user_model().objects.get(email="rae@neworg.org")
    user.groups.add(founding_partners_group())  # what the Stripe webhook does
    r = c.get("/portal/", HTTP_HOST="localhost")
    assert r.status_code == 302 and "/intake/" in r["Location"]
    # activate page now bounces them onward too
    r = c.get("/activate/", HTTP_HOST="localhost")
    assert r.status_code == 302


def test_signin_page_offers_account_creation_and_support():
    r = Client().get("/accounts/login/", HTTP_HOST="localhost")
    body = r.content.decode()
    assert "Create an account" in body
    assert "/accounts/signup/" in body
    assert "Message support" in body


def test_duplicate_active_email_rejected():
    u = get_user_model().objects.create_user(username="rae@neworg.org", email="rae@neworg.org")
    u.set_password("existing-pass-1"); u.save()
    r = Client().post("/accounts/signup/", SIGNUP, HTTP_HOST="localhost")
    assert r.status_code == 200
    assert b"sign in instead" in r.content


def test_password_less_webhook_account_cannot_be_claimed_via_signup():
    # The Stripe webhook provisions buyers WITHOUT a usable password; they claim
    # the account via their emailed password-set link. Until then, a public
    # signup POST with the buyer's email must not take over the paid seat.
    u = get_user_model().objects.create_user(username="rae@neworg.org", email="rae@neworg.org")
    u.set_unusable_password(); u.save()
    r = Client().post("/accounts/signup/", SIGNUP, HTTP_HOST="localhost")
    assert r.status_code == 200
    assert b"sign in instead" in r.content
    u.refresh_from_db()
    assert not u.has_usable_password()
    assert get_user_model().objects.filter(email__iexact="rae@neworg.org").count() == 1


def test_webhook_purchase_verifies_account(mailoutbox):
    # Full loop: self-signup (unverified) -> Stripe purchase (same email) -> verified.
    from unittest.mock import patch
    c = Client()
    c.post("/accounts/signup/", SIGNUP, HTTP_HOST="localhost")
    event = {"type": "checkout.session.completed",
             "data": {"object": {"id": "cs_1", "customer_details": {"email": "rae@neworg.org", "name": "Rae Kim"}}}}
    with patch.dict("os.environ", {"STRIPE_WEBHOOK_SECRET": "whsec_test"}), \
         patch("openoutreach.signals.billing.stripe.Webhook.construct_event", return_value=event):
        resp = Client().post("/billing/stripe-webhook/", data=b"{}", content_type="application/json",
                             HTTP_STRIPE_SIGNATURE="sig", HTTP_HOST="localhost")
    assert resp.status_code == 200
    r = c.get("/portal/", HTTP_HOST="localhost")
    assert r.status_code == 302 and "/intake/" in r["Location"]
