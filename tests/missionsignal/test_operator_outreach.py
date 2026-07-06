"""Operator outreach cockpit: compose deterministic drafts, edit, and send
server-side (replaces the local n8n digest). Staff-gated; every send is a
deliberate per-lead action, never an automated blast.
"""
import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse

from openoutreach.signals.models import SalesLead
from openoutreach.signals.outreach import compose_outreach_email, outreach_queue

pytestmark = pytest.mark.django_db


@pytest.fixture
def staff(db):
    return get_user_model().objects.create_user(username="ops", password="x", is_staff=True)


def _lead(**kw):
    defaults = dict(name="Dana Reed", organization="Bright Paths", email="dana@brightpaths.org",
                    list_segment="warm", warmth="hot", email_status="not_sent")
    defaults.update(kw)
    return SalesLead.objects.create(**defaults)


# ── compose ───────────────────────────────────────────────────────────────────

def test_compose_warm_vs_cold_and_video():
    warm = _lead(list_segment="warm", why_fit="we worked together at Aeras")
    subject, body = compose_outreach_email(warm)
    assert "Dana" in body
    assert "we worked together at Aeras" in body
    assert "youtu.be/FBvLg9c35Qo" in body  # sales walkthrough always present
    assert "Bright Paths" in subject

    cold = _lead(name="Sam Cole", organization="Metro Coalition", email="s@metro.org",
                 list_segment="cold_florida_crm", warmth="cold")
    _s, cold_body = compose_outreach_email(cold)
    assert "founder of Anansi Atlas" in cold_body  # cold opener


def test_saved_edit_used_over_fresh_compose():
    from openoutreach.signals.outreach import draft_for
    lead = _lead(outreach_draft="My hand-edited version.")
    _subject, body = draft_for(lead)
    assert body == "My hand-edited version."


# ── queue ordering ────────────────────────────────────────────────────────────

def test_queue_hottest_first_and_excludes_sent_and_no_email():
    _lead(name="A Cold", organization="Zeta", email="a@z.org", list_segment="cold_florida_crm", warmth="cold")
    _lead(name="B Hot", organization="Alpha", email="b@a.org", list_segment="warm", warmth="hot")
    _lead(name="C Sent", organization="Beta", email="c@b.org", email_status="sent")
    _lead(name="D NoEmail", organization="Gamma", email="", list_segment="warm", warmth="hot")
    queue = outreach_queue()
    names = [l.name for l in queue]
    assert names == ["B Hot", "A Cold"]  # warm-hot first, cold last; sent + no-email excluded


# ── cockpit page + gating ─────────────────────────────────────────────────────

def test_cockpit_lists_leads_for_staff(client, staff):
    _lead()
    client.force_login(staff)
    body = client.get(reverse("operator-outreach")).content.decode()
    assert "Dana Reed" in body
    assert "youtu.be/FBvLg9c35Qo" in body
    assert "Send" in body


def test_cockpit_requires_staff(client):
    user = get_user_model().objects.create_user(username="notstaff", password="x")
    client.force_login(user)
    response = client.get(reverse("operator-outreach"))
    assert response.status_code in (302, 403)  # staff_member_required bounces


# ── send + save ───────────────────────────────────────────────────────────────

def test_send_emails_lead_marks_sent(client, staff, settings):
    # Reply-To stamping is covered by test_email_reply_to.py; here the test
    # runner's locmem backend captures the message so we assert send + mark.
    settings.DEFAULT_FROM_EMAIL = "mail@anansiatlas.com"
    lead = _lead()
    client.force_login(staff)
    response = client.post(reverse("operator-outreach-send", kwargs={"pk": lead.pk}),
                           {"subject": "Hi Dana", "body": "Edited body here."})
    assert response.status_code == 302
    assert len(mail.outbox) == 1
    msg = mail.outbox[0]
    assert msg.to == ["dana@brightpaths.org"]
    assert msg.subject == "Hi Dana"
    assert "Edited body here." in msg.body
    lead.refresh_from_db()
    assert lead.email_status == "sent"
    assert lead.outreach_draft == "Edited body here."


def test_send_is_idempotent_no_double_send(client, staff):
    lead = _lead(email_status="sent")
    client.force_login(staff)
    client.post(reverse("operator-outreach-send", kwargs={"pk": lead.pk}),
                {"subject": "x", "body": "y"})
    assert len(mail.outbox) == 0  # already sent → skipped


def test_save_draft_persists_without_sending(client, staff):
    lead = _lead()
    client.force_login(staff)
    client.post(reverse("operator-outreach-save", kwargs={"pk": lead.pk}),
                {"subject": "Draft subject", "body": "Draft body, not sent."})
    assert len(mail.outbox) == 0
    lead.refresh_from_db()
    assert lead.outreach_draft == "Draft body, not sent."
    assert lead.subject_line == "Draft subject"
    assert lead.email_status == "not_sent"
