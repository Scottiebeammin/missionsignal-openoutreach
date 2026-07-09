"""Anti-spam honeypot on the public signup/question forms, and the operator
waitlist Delete action."""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from openoutreach.signals.models import InterestSignup

pytestmark = pytest.mark.django_db

GOOD = {"name": "Jane Real", "organization": "Bright Org", "email": "jane@bright.org",
        "role": "Executive Director", "interest_type": "founding_atlas_partners", "message": ""}


def test_real_signup_is_saved(client):
    resp = client.post(reverse("anansi-atlas-landing"), GOOD)
    assert resp.status_code == 302
    assert InterestSignup.objects.filter(email="jane@bright.org").exists()


def test_honeypot_blocks_a_bot_signup(client):
    # A bot fills the hidden 'company_website' field; humans never see it.
    resp = client.post(reverse("anansi-atlas-landing"), {**GOOD, "company_website": "http://spam.ru"})
    assert resp.status_code == 302                       # silently "accepted"
    assert not InterestSignup.objects.filter(email="jane@bright.org").exists()   # but nothing saved


def test_honeypot_blocks_a_bot_question(client):
    resp = client.post(reverse("ask-question"),
                       {"name": "Bot", "email": "bot@spam.ru", "message": "buy now",
                        "company_website": "http://spam.ru"})
    assert resp.status_code == 302
    assert InterestSignup.objects.count() == 0


def test_operator_can_delete_a_waitlist_entry(client):
    staff = get_user_model().objects.create_user(username="ops", password="x", is_staff=True)
    s = InterestSignup.objects.create(name="Spammy", email="x@spam.ru", organization="X")
    client.force_login(staff)
    resp = client.post(reverse("operator-waitlist-delete", kwargs={"pk": s.pk}))
    assert resp.status_code == 302
    assert not InterestSignup.objects.filter(pk=s.pk).exists()


def test_delete_requires_staff(client):
    s = InterestSignup.objects.create(name="Keep", email="k@org.org")
    resp = client.post(reverse("operator-waitlist-delete", kwargs={"pk": s.pk}))
    assert resp.status_code in (302, 403)                # bounced to login, not deleted
    assert InterestSignup.objects.filter(pk=s.pk).exists()
