"""Primary-angle tracking: can a follow-up tell it is repeating itself?

Before OutreachMessage existed, the only record of a previous email was its prose,
appended into SalesLead.notes — which also held the researched profile and the
operator's notes, all three fed to the model as one "Notes:" blob. "Is this a new
argument?" was a judgement call nobody could audit, and the answer was usually no:
ten drafts, one idea, reworded.

These test the invariants, not the prompt wording.
"""
from __future__ import annotations

import pytest
from django.core import mail
from django.urls import reverse

from openoutreach.signals.models import (
    ANGLE_FAMILY,
    OutreachAngle,
    OutreachMessage,
    SalesLead,
    angle_family,
    angle_is_materially_new,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def campaign(db):
    """The campaign the drafting command reads its docs from."""
    from openoutreach.core.models import Campaign
    return Campaign.objects.get_or_create(
        name="Anansi Atlas — Founding Cohort",
        defaults={"product_docs": "docs", "campaign_objective": "obj"})[0]


@pytest.fixture
def staff(db):
    from django.contrib.auth import get_user_model
    return get_user_model().objects.create_user(username="ops", password="x", is_staff=True)


def _lead(**kw):
    return SalesLead.objects.create(**{
        "name": "Dana Reed", "organization": "Brightpaths", "email": "dana@brightpaths.org",
        "email_status": "not_sent",
        **kw,
    })


# ── taxonomy ────────────────────────────────────────────────────────────────

def test_every_angle_has_a_family():
    # An unmapped angle silently becomes "unknown" and stops being comparable,
    # which quietly disables the whole mechanism for that value.
    unmapped = [a.value for a in OutreachAngle
                if a != OutreachAngle.UNCLASSIFIED and a.value not in ANGLE_FAMILY]
    assert unmapped == []


def test_taxonomy_spans_more_than_funding():
    # Atlas surfaces partnerships, free resources, technical assistance and
    # readiness too. A funding-only taxonomy pushes every email back onto funding.
    assert set(ANGLE_FAMILY.values()) >= {"funding", "partnership", "resource", "readiness"}


def test_angle_family_is_unknown_for_unrecognised_values():
    assert angle_family("something_invented") == "unknown"
    assert angle_family("") == "unknown"


# ── the "is this actually new?" rule ────────────────────────────────────────

def test_repeating_the_same_angle_is_not_new():
    assert not angle_is_materially_new(
        OutreachAngle.COUNTY_FUNDING, OutreachAngle.COUNTY_FUNDING)


def test_crossing_value_families_is_new():
    # The user's own examples: county funding → free technical assistance,
    # contract expiry → readiness gap.
    assert angle_is_materially_new(
        OutreachAngle.COUNTY_FUNDING, OutreachAngle.TECHNICAL_ASSISTANCE)
    assert angle_is_materially_new(
        OutreachAngle.CONTRACT_EXPIRATION, OutreachAngle.READINESS_GAP)
    assert angle_family(OutreachAngle.COUNTY_FUNDING) != angle_family(
        OutreachAngle.TECHNICAL_ASSISTANCE)


def test_a_different_angle_in_the_same_family_still_counts_as_new():
    assert angle_is_materially_new(
        OutreachAngle.COUNTY_FUNDING, OutreachAngle.STATE_FUNDING)


def test_no_recorded_previous_angle_permits_anything():
    # Legacy leads emailed before this existed have no angle. They must not be
    # blocked from a follow-up.
    assert angle_is_materially_new("", OutreachAngle.COUNTY_FUNDING)
    assert angle_is_materially_new(OutreachAngle.UNCLASSIFIED, OutreachAngle.COUNTY_FUNDING)


# ── persistence ─────────────────────────────────────────────────────────────

def test_angle_persists_on_the_message():
    lead = _lead()
    msg = OutreachMessage.objects.create(
        lead=lead, primary_angle=OutreachAngle.CONTRACT_EXPIRATION,
        angle_detail="CINS/FINS contract through 2026-06-30")
    msg.refresh_from_db()
    assert msg.primary_angle == OutreachAngle.CONTRACT_EXPIRATION
    assert msg.angle_detail == "CINS/FINS contract through 2026-06-30"
    assert msg.angle_family == "funding"


def test_last_for_prefers_a_sent_message_over_a_later_draft():
    # A draft the recipient never received is not the previous touch. Treating it
    # as one would make a follow-up avoid an argument that was never made.
    lead = _lead()
    sent = OutreachMessage.objects.create(
        lead=lead, primary_angle=OutreachAngle.COUNTY_FUNDING,
        status=OutreachMessage.Status.SENT)
    OutreachMessage.objects.create(
        lead=lead, primary_angle=OutreachAngle.FREE_RESOURCE,
        status=OutreachMessage.Status.DRAFTED)
    assert OutreachMessage.last_for(lead, sent_only=True).pk == sent.pk


def test_last_for_is_scoped_to_its_own_lead():
    a, b = _lead(), _lead(email="other@elsewhere.org", organization="Elsewhere")
    OutreachMessage.objects.create(lead=a, primary_angle=OutreachAngle.COUNTY_FUNDING)
    assert OutreachMessage.last_for(b) is None


# ── the send path ───────────────────────────────────────────────────────────

def test_sending_marks_the_drafted_message_sent_with_a_timestamp(client, staff, settings):
    settings.DEFAULT_FROM_EMAIL = "mail@anansiatlas.com"
    lead = _lead()
    msg = OutreachMessage.objects.create(
        lead=lead, primary_angle=OutreachAngle.COUNTY_FUNDING,
        status=OutreachMessage.Status.DRAFTED)
    client.force_login(staff)
    client.post(reverse("operator-outreach-send", kwargs={"pk": lead.pk}),
                {"subject": "hi", "body": "b"})
    msg.refresh_from_db()
    assert msg.status == OutreachMessage.Status.SENT
    assert msg.sent_at is not None
    # The angle survives the send — it is what the follow-up will read.
    assert msg.primary_angle == OutreachAngle.COUNTY_FUNDING


def test_a_send_with_no_drafted_message_still_records_one(client, staff, settings):
    # Sends that bypass the drafting command (a hand-written cockpit email) must
    # still leave a record, or the follow-up has no idea a touch happened.
    settings.DEFAULT_FROM_EMAIL = "mail@anansiatlas.com"
    lead = _lead()
    client.force_login(staff)
    client.post(reverse("operator-outreach-send", kwargs={"pk": lead.pk}),
                {"subject": "hi", "body": "b"})
    msg = OutreachMessage.last_for(lead, sent_only=True)
    assert msg is not None and msg.status == OutreachMessage.Status.SENT
    # No angle was chosen by a model, so none is claimed.
    assert msg.primary_angle == ""


def test_a_blocked_send_leaves_the_message_unsent(client, staff, settings):
    # Opt-out is enforced in send_outreach_email. The message must not be marked
    # sent, and no follow-up timer may start from it.
    from openoutreach.signals.unsubscribe import record_opt_out

    settings.DEFAULT_FROM_EMAIL = "mail@anansiatlas.com"
    lead = _lead()
    msg = OutreachMessage.objects.create(
        lead=lead, status=OutreachMessage.Status.DRAFTED,
        primary_angle=OutreachAngle.COUNTY_FUNDING)
    record_opt_out(lead.email)
    client.force_login(staff)
    client.post(reverse("operator-outreach-send", kwargs={"pk": lead.pk}),
                {"subject": "hi", "body": "b"})
    msg.refresh_from_db()
    assert msg.status == OutreachMessage.Status.DRAFTED
    assert msg.sent_at is None
    assert mail.outbox == []


# ── the follow-up prompt actually receives the prior angle ──────────────────

def _followup_prompt(lead):
    """Render the real follow-up prompt for a lead, via the command's own path."""
    from django.core.management import call_command
    from io import StringIO

    out = StringIO()
    call_command("preview_cohort_drafts", "--prompt-only", "--followup",
                 "--lead", str(lead.pk), stdout=out)
    return out.getvalue()


def test_followup_prompt_carries_the_prior_angle_and_detail(campaign):
    lead = _lead(list_segment="cold_florida_crm", email_status="sent")
    OutreachMessage.objects.create(
        lead=lead, primary_angle=OutreachAngle.COUNTY_FUNDING,
        angle_detail="Marion County SHIP allocation",
        status=OutreachMessage.Status.SENT)
    prompt = _followup_prompt(lead)
    # The invariant: the prior angle reaches the writer as structured data, not as
    # prose it has to infer from.
    assert OutreachAngle.COUNTY_FUNDING in prompt
    assert "Marion County SHIP allocation" in prompt
    assert "funding" in prompt


def test_followup_prompt_says_so_when_no_prior_angle_was_recorded(campaign):
    # Leads emailed before angle tracking existed. The prompt must admit it does
    # not know rather than let the model invent what the opener argued.
    lead = _lead(list_segment="cold_florida_crm", email_status="sent")
    prompt = _followup_prompt(lead)
    assert "No angle was recorded" in prompt


def test_the_angle_menu_reaches_every_draft_prompt(campaign):
    lead = _lead(list_segment="cold_florida_crm")
    prompt = _followup_prompt(lead)
    # All four families offered, so the writer is not funnelled back onto funding.
    for family in ("funding", "partnership", "resource", "readiness"):
        assert f"**{family}:**" in prompt
    assert OutreachAngle.TECHNICAL_ASSISTANCE in prompt
    assert OutreachAngle.PARTNERSHIP_PATHWAY in prompt
