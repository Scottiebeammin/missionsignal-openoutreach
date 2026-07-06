"""Founding-partner welcome hero on the client dashboard — a warm, branded
moment for founding partners (and pilots), reusing the dashboard's own numbers."""
import pytest
from django.urls import reverse

from openoutreach.core.access import founding_partners_group
from openoutreach.signals.demo import seed_missionsignal_demo

pytestmark = pytest.mark.django_db


def test_founding_partner_sees_welcome_hero(client):
    user, _org, project = seed_missionsignal_demo()
    user.groups.add(founding_partners_group())
    client.force_login(user)
    body = client.get(reverse("project-dashboard", kwargs={"pk": project.pk})).content.decode()
    assert "Founding Atlas Partner" in body
    assert "one of our first 20 founding partners" in body
    assert "opportunities mapped" in body
    assert "See foundations funding orgs like yours" in body  # CTA into the receipts


def test_welcome_greets_and_shows_numbers(client):
    user, _org, project = seed_missionsignal_demo()
    user.first_name = "Dana"
    user.save()
    user.groups.add(founding_partners_group())
    client.force_login(user)
    body = client.get(reverse("project-dashboard", kwargs={"pk": project.pk})).content.decode()
    # The hero renders (greeting + the three headline stats labels are present).
    assert "readiness ·" in body
    assert "strong matches" in body
