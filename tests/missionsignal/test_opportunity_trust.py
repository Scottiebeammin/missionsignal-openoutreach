"""Opportunity trust tier: a client-facing 'Confirmed' opportunity must be
human-verified AND backed by a real (non-placeholder) source link. Operators can
verify with one click."""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from openoutreach.core.models import Organization, Project
from openoutreach.funding.models import Opportunity

pytestmark = pytest.mark.django_db


def _opp(**kw):
    defaults = dict(name="Youth Grant", verification_status="verified",
                    source_urls=["https://realfunder.org/grants"])
    defaults.update(kw)
    return Opportunity.objects.create(**defaults)


def test_real_source_url_skips_placeholders():
    o = _opp(source_urls=["https://demo.example.org/x", "https://realfunder.org/apply"])
    assert o.real_source_url() == "https://realfunder.org/apply"
    assert _opp(source_urls=["https://foo.example.org"]).real_source_url() is None
    assert _opp(source_urls=[]).real_source_url() is None


def test_is_confirmed_requires_verified_and_real_source():
    assert _opp(verification_status="verified", source_urls=["https://realfunder.org"]).is_confirmed is True
    # verified but only a placeholder URL → NOT confirmed
    assert _opp(verification_status="verified", source_urls=["https://x.example.org"]).is_confirmed is False
    # real source but not verified → NOT confirmed
    assert _opp(verification_status="unverified", source_urls=["https://realfunder.org"]).is_confirmed is False


def test_operator_verify_action(client):
    staff = get_user_model().objects.create_user(username="ops", password="x", is_staff=True)
    o = _opp(verification_status="unverified", source_urls=["https://realfunder.org/apply"])
    client.force_login(staff)
    resp = client.post(reverse("operator-opportunity-verify", kwargs={"pk": o.pk}))
    assert resp.status_code == 302
    o.refresh_from_db()
    assert o.verification_status == "verified"
    assert o.is_confirmed is True                 # real source + now verified


def test_verify_requires_staff(client):
    o = _opp(verification_status="unverified")
    resp = client.post(reverse("operator-opportunity-verify", kwargs={"pk": o.pk}))
    assert resp.status_code in (302, 403)
    o.refresh_from_db()
    assert o.verification_status == "unverified"   # not verified by a non-staff request
