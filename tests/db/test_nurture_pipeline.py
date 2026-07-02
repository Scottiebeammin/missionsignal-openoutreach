"""Nurture sequence completion feeds the SalesLead pipeline."""

from datetime import timedelta

import pytest
from django.utils import timezone

from openoutreach.signals.models import InterestSignup, SalesLead
from openoutreach.signals.nurture import send_due_nurture_emails

pytestmark = pytest.mark.django_db


def test_completed_sequence_creates_inbound_nurturing_lead(mailoutbox):
    signup = InterestSignup.objects.create(
        name="Alex Doe", organization="Hope Works", email="alex@hopeworks.org",
        nurture_step=2,  # step 3 (day 7) is due
    )
    InterestSignup.objects.filter(pk=signup.pk).update(
        created_at=timezone.now() - timedelta(days=8)
    )
    sent, skipped = send_due_nurture_emails()
    assert sent == 1
    lead = SalesLead.objects.get(email="alex@hopeworks.org")
    assert lead.source == SalesLead.Source.INBOUND
    assert lead.status == SalesLead.Status.NURTURING

    # idempotent — running again doesn't duplicate
    send_due_nurture_emails()
    assert SalesLead.objects.filter(email="alex@hopeworks.org").count() == 1
