"""Repeat submissions from the same address collapse to one row.

The waitlist table reached 4,132 rows across roughly 990 distinct addresses —
the same handful of bot addresses posting the same form over and over. The
honeypot only catches bots that fill every visible field; the ones posting the
form directly walked straight past it. This keeps one row per address per form
per day, which is all a real person would ever generate.
"""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from openoutreach.signals.models import InterestSignup

pytestmark = pytest.mark.django_db

_WAITLIST_POST = {
    "name": "Alex Doe",
    "organization": "Hope Works",
    "email": "alex@hopeworks.org",
    "interest_type": InterestSignup.InterestType.FOUNDING_ATLAS_PARTNERS,
}


def test_second_identical_waitlist_submission_creates_no_row(client):
    url = reverse("anansi-atlas-landing")

    client.post(url, _WAITLIST_POST)
    client.post(url, _WAITLIST_POST)

    assert InterestSignup.objects.filter(email="alex@hopeworks.org").count() == 1


def test_repeat_submission_still_lands_on_the_thanks_page(client):
    url = reverse("anansi-atlas-landing")
    client.post(url, _WAITLIST_POST)

    response = client.post(url, _WAITLIST_POST)

    assert response.status_code == 302
    assert response.url == reverse("anansi-atlas-thanks")


def test_a_different_form_from_the_same_person_is_not_a_repeat(client):
    """Asking a question and later joining the waitlist are two real submissions."""
    client.post(reverse("anansi-atlas-landing"), _WAITLIST_POST)
    client.post(
        reverse("ask-question"),
        {"name": "Alex Doe", "email": "alex@hopeworks.org", "message": "How does pricing work?"},
    )

    rows = InterestSignup.objects.filter(email="alex@hopeworks.org")
    assert rows.count() == 2
    assert set(rows.values_list("interest_type", flat=True)) == {
        InterestSignup.InterestType.FOUNDING_ATLAS_PARTNERS,
        InterestSignup.InterestType.QUESTION,
    }


def test_the_same_person_may_sign_up_again_after_the_window(client):
    url = reverse("anansi-atlas-landing")
    client.post(url, _WAITLIST_POST)
    InterestSignup.objects.filter(email="alex@hopeworks.org").update(
        created_at=timezone.now() - timedelta(days=2)
    )

    client.post(url, _WAITLIST_POST)

    assert InterestSignup.objects.filter(email="alex@hopeworks.org").count() == 2


def test_honeypot_still_drops_the_bots_that_fill_it(client):
    client.post(
        reverse("anansi-atlas-landing"),
        {**_WAITLIST_POST, "company_website": "http://spam.example"},
    )

    assert not InterestSignup.objects.exists()
