"""A cron that cannot send must fail, not report success.

All three of these jobs shipped with their EMAIL_* variables declared `sync: false`
and never set, so every send raised ConnectionRefusedError, every exception was
swallowed per-recipient, and every run exited 0. Render showed a month of green
ticks over total failure. These tests pin the opposite behaviour.
"""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from openoutreach.core.models import Organization, Project
from openoutreach.funding.models import Opportunity
from openoutreach.funding import relevance
from openoutreach.signals import notifications

pytestmark = pytest.mark.django_db


def _project_with_owner(name="Women on the Rise", email="owner@wotr.org"):
    organization = Organization.objects.create(name=name, mission="Serve the community.")
    project = Project.objects.create(name=name, organization=organization)
    owner = get_user_model().objects.create_user(
        username=email, email=email, password="not-a-real-password"
    )
    project.users.add(owner)
    return project


def _tracked_opportunity(project, name="County workforce grant", days=21):
    return Opportunity.objects.create(
        project=project,
        name=name,
        deadline=timezone.localdate() + timedelta(days=days),
        is_interested=True,
    )


# ------------------------------------------------ send_interest_reminders

def test_reminders_exit_non_zero_when_every_send_fails(monkeypatch):
    project = _project_with_owner()
    _tracked_opportunity(project)
    monkeypatch.setattr(notifications, "send_interest_reminder", lambda *a, **k: False)

    with pytest.raises(CommandError, match="Every reminder send failed"):
        call_command("send_interest_reminders")


def test_reminders_succeed_when_the_transport_works(mailoutbox):
    project = _project_with_owner()
    _tracked_opportunity(project)

    call_command("send_interest_reminders")

    assert len(mailoutbox) == 1


def test_reminders_stay_green_when_there_is_nothing_to_send(monkeypatch):
    """No tracked opportunities is not a failure."""
    monkeypatch.setattr(notifications, "send_interest_reminder", lambda *a, **k: False)
    _project_with_owner()

    call_command("send_interest_reminders")  # must not raise


# ------------------------------------------------ send_opportunity_alerts

def _make_everything_relevant(monkeypatch):
    """Neutralise the matching filters — these tests are about failure accounting,
    not about which opportunities qualify for an alert."""
    monkeypatch.setattr(relevance, "opportunity_relevance", lambda *a, **k: 1)
    monkeypatch.setattr(relevance, "is_off_geography", lambda *a, **k: False)
    monkeypatch.setattr(relevance, "is_research_grant", lambda *a, **k: False)


def test_alerts_exit_non_zero_when_every_send_fails(monkeypatch):
    project = _project_with_owner()
    # A deadline milestone the alert command looks for (exactly 7 days out).
    _tracked_opportunity(project, name="Community foundation grant", days=7)
    _make_everything_relevant(monkeypatch)
    monkeypatch.setattr(notifications, "send_opportunity_alert", lambda *a, **k: False)

    with pytest.raises(CommandError, match="Every alert send failed"):
        call_command("send_opportunity_alerts")


def test_alerts_stay_green_when_there_is_nothing_to_send(monkeypatch):
    monkeypatch.setattr(notifications, "send_opportunity_alert", lambda *a, **k: False)
    _project_with_owner()

    call_command("send_opportunity_alerts")  # must not raise
