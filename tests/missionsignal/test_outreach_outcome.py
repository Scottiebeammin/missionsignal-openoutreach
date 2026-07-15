"""Outreach reply/response tracking: sending sets 'awaiting', the operator logs
what came back, the Sent tab lists them, and the header shows a response rate."""
import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse

from openoutreach.signals.models import SalesLead

pytestmark = pytest.mark.django_db


@pytest.fixture
def staff(db):
    return get_user_model().objects.create_user(username="ops", password="x", is_staff=True)


def _lead(**kw):
    d = dict(name="Dana", organization="Bright", email="d@bright.org",
             list_segment="warm", warmth="hot", email_status="not_sent")
    d.update(kw)
    return SalesLead.objects.create(**d)


def test_send_sets_outcome_awaiting(client, staff, settings):
    settings.DEFAULT_FROM_EMAIL = "mail@anansiatlas.com"
    lead = _lead()
    client.force_login(staff)
    client.post(reverse("operator-outreach-send", kwargs={"pk": lead.pk}),
                {"subject": "hi", "body": "b", "tab": "warm"})
    assert len(mail.outbox) == 1
    lead.refresh_from_db()
    assert lead.outreach_outcome == "awaiting"


def test_log_outcome_interested(client, staff):
    lead = _lead(email_status="sent", outreach_outcome="awaiting")
    client.force_login(staff)
    client.post(reverse("operator-outreach-outcome", kwargs={"pk": lead.pk}),
                {"outcome": "interested", "tab": "sent"})
    lead.refresh_from_db()
    assert lead.outreach_outcome == "interested"


def test_log_meeting_advances_stage(client, staff):
    lead = _lead(email_status="sent", outreach_outcome="awaiting", status="reached_out")
    client.force_login(staff)
    client.post(reverse("operator-outreach-outcome", kwargs={"pk": lead.pk}),
                {"outcome": "meeting", "tab": "sent"})
    lead.refresh_from_db()
    assert lead.outreach_outcome == "meeting"
    assert lead.status == "call_scheduled"


def test_sent_tab_lists_and_shows_response_rate(client, staff):
    _lead(email_status="sent", outreach_outcome="awaiting", name="A")
    _lead(email="b@x.org", email_status="sent", outreach_outcome="interested", name="B")
    _lead(email="c@x.org", email_status="not_sent", name="C")   # not sent → not on the tab
    client.force_login(staff)
    body = client.get(reverse("operator-outreach") + "?tab=sent").content.decode()
    assert "A" in body and "B" in body
    assert "Response rate" in body
    assert "50%" in body                     # 1 of 2 sent responded
