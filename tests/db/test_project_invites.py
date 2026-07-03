"""Signed project invite links (openoutreach/signals/invites.py)."""

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from openoutreach.signals.invites import make_invite_token

pytestmark = pytest.mark.django_db


@pytest.fixture
def project(db):
    from openoutreach.core.models import Organization, Project
    org = Organization.objects.create(name="Empowered Girls Inc.", mission="Empowering girls 9-18.")
    return Project.objects.create(name="Empowered Girls Inc.", organization=org)


def _accept_url(project):
    return f"/invite/{make_invite_token(project.pk)}/"


def test_invite_page_renders(project):
    r = Client().get(_accept_url(project), HTTP_HOST="localhost")
    assert r.status_code == 200
    assert b"Empowered Girls Inc." in r.content


def test_invite_creates_account_attaches_and_logs_in(project):
    c = Client()
    r = c.post(_accept_url(project), {
        "first_name": "Dana", "last_name": "Lee",
        "email": "dana@empoweredgirls.org",
        "password1": "web-of-opportunity-9", "password2": "web-of-opportunity-9",
    }, HTTP_HOST="localhost")
    assert r.status_code == 302 and f"/projects/{project.pk}/dashboard/" in r["Location"]
    user = get_user_model().objects.get(email="dana@empoweredgirls.org")
    assert project.users.filter(pk=user.pk).exists()
    assert user.has_usable_password()
    # logged in — portal page loads without login redirect
    r2 = c.get(f"/projects/{project.pk}/organization/", HTTP_HOST="localhost")
    assert r2.status_code == 200


def test_invite_reuses_webhook_provisioned_user(project):
    # A user pre-created without a usable password (e.g. by the Stripe webhook)
    # can claim the invite with the same email instead of erroring.
    u = get_user_model().objects.create_user(username="dana@empoweredgirls.org", email="dana@empoweredgirls.org")
    u.set_unusable_password(); u.save()
    r = Client().post(_accept_url(project), {
        "first_name": "Dana", "email": "dana@empoweredgirls.org",
        "password1": "web-of-opportunity-9", "password2": "web-of-opportunity-9",
    }, HTTP_HOST="localhost")
    assert r.status_code == 302
    assert get_user_model().objects.filter(email__iexact="dana@empoweredgirls.org").count() == 1
    assert project.users.count() == 1


def test_existing_active_account_is_told_to_sign_in(project):
    u = get_user_model().objects.create_user(username="dana@empoweredgirls.org", email="dana@empoweredgirls.org")
    u.set_password("already-set-42"); u.save()
    r = Client().post(_accept_url(project), {
        "first_name": "Dana", "email": "dana@empoweredgirls.org",
        "password1": "web-of-opportunity-9", "password2": "web-of-opportunity-9",
    }, HTTP_HOST="localhost")
    assert r.status_code == 200
    assert b"sign in instead" in r.content


def test_tampered_or_expired_token_rejected(project):
    r = Client().get("/invite/garbage-token/", HTTP_HOST="localhost")
    assert r.status_code == 410
    with patch("openoutreach.signals.invites.INVITE_MAX_AGE_DAYS", 0):
        r = Client().get(_accept_url(project), HTTP_HOST="localhost")
    assert r.status_code == 410
