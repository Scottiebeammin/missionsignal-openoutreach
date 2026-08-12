"""Prospect disposition, and the separation of evidence from commentary.

Two problems, one pass.

The old DROPPED mechanism set `status=passed` and wrote the reason into `notes`. That
looked like a gate but wasn't: the passed filter existed only in the `--sample`
queryset, so `--lead N` walked straight past it, and `send_outreach_email` never
checked it at all. A "dropped" lead could still be drafted by id and still be sent
from the cockpit.

And `notes` carried researched profile, archived prior emails and operator commentary
in one field, all handed to the writer under "Notes:" — so "probably short-staffed"
could come back as "with your staffing challenges".

Behaviour and invariants, not prose.
"""
from __future__ import annotations

import datetime as dt

import pytest
from django.core import mail
from django.urls import reverse

from openoutreach.core.management.commands.preview_cohort_drafts import (
    _lead_facts,
    _relationship_block,
)
from openoutreach.signals.models import (
    AUTO_DISQUALIFY_REASONS,
    CONTACT_SCOPED_REASONS,
    DispositionReason,
    OutreachAngle,
    OutreachMessage,
    SalesLead,
    disposition_for,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def staff(db):
    from django.contrib.auth import get_user_model
    return get_user_model().objects.create_user(username="ops", password="x", is_staff=True)


def _lead(**kw):
    return SalesLead.objects.create(**{
        "name": "Dana Reed", "organization": "Brightpaths", "email": "dana@brightpaths.org",
        "email_status": "not_sent", "list_segment": SalesLead.Segment.COLD_FLORIDA_CRM,
        **kw,
    })


def _send(client, staff, lead):
    client.force_login(staff)
    return client.post(reverse("operator-outreach-send", kwargs={"pk": lead.pk}),
                       {"subject": "hi", "body": "b"})


# ── the deterministic mapping ───────────────────────────────────────────────

def test_eligible_by_default():
    assert _lead().disposition == SalesLead.DISPOSITION_ELIGIBLE


def test_settled_organization_facts_disqualify():
    for reason in (DispositionReason.ORGANIZATION_CLOSED,
                   DispositionReason.WRONG_GEOGRAPHY,
                   DispositionReason.WRONG_ORGANIZATION_TYPE,
                   DispositionReason.ALREADY_CUSTOMER):
        disposition, scope = disposition_for(reason)
        assert disposition == "disqualified", reason
        assert scope == "organization"


def test_uncertainty_routes_to_review_never_rejection():
    # Conflicting or thin evidence is a reason for a human to look, not to reject.
    for reason in (DispositionReason.CONFLICTING_RESEARCH,
                   DispositionReason.STALE_RESEARCH,
                   DispositionReason.NEEDS_HUMAN_REVIEW):
        assert disposition_for(reason)[0] == "review", reason


def test_stale_evidence_downgrades_a_disqualification_to_review():
    # A historically accurate fact is not grounds for a present-tense exclusion.
    assert disposition_for(DispositionReason.ORGANIZATION_CLOSED)[0] == "disqualified"
    assert disposition_for(DispositionReason.ORGANIZATION_CLOSED,
                           evidence_is_current=False)[0] == "review"


def test_weak_personalization_never_disqualifies():
    # Category-relevant outreach is legitimate. Knowing only a few facts about an
    # organization is not evidence that the campaign is wrong for it.
    assert DispositionReason.INSUFFICIENT_RELEVANCE not in AUTO_DISQUALIFY_REASONS
    assert disposition_for(DispositionReason.INSUFFICIENT_RELEVANCE)[0] == "review"


def test_a_thin_profile_lead_stays_eligible():
    lead = _lead(research_profile="", why_fit="")
    assert lead.cold_outreach_block() == ""


# ── contact vs organization ─────────────────────────────────────────────────

def test_contact_problems_are_scoped_to_the_contact_not_the_org():
    # A departed ED does not close a charity.
    for reason in CONTACT_SCOPED_REASONS:
        disposition, scope = disposition_for(reason)
        assert scope == "contact", reason
        assert disposition == "review", reason


def test_contact_left_does_not_disqualify_the_organization():
    lead = _lead()
    lead.set_disposition(DispositionReason.CONTACT_LEFT_ORGANIZATION, detail="ED moved on")
    assert lead.disposition == SalesLead.DISPOSITION_REVIEW
    assert lead.disposition_scope == "contact"
    assert lead.disposition != SalesLead.DISPOSITION_DISQUALIFIED


def test_an_invalid_contact_still_cannot_be_emailed(client, staff, settings):
    # Scoped to the contact, but this lead IS that contact — it must not send.
    settings.DEFAULT_FROM_EMAIL = "mail@anansiatlas.com"
    lead = _lead()
    lead.set_disposition(DispositionReason.CONTACT_LEFT_ORGANIZATION)
    lead.save()
    _send(client, staff, lead)
    assert mail.outbox == []


# ── the authoritative gate ──────────────────────────────────────────────────

@pytest.mark.parametrize("reason", [
    DispositionReason.ORGANIZATION_CLOSED,      # disqualified
    DispositionReason.CONFLICTING_RESEARCH,     # review
])
def test_a_held_lead_cannot_be_sent_from_the_cockpit(client, staff, settings, reason):
    settings.DEFAULT_FROM_EMAIL = "mail@anansiatlas.com"
    lead = _lead()
    lead.set_disposition(reason)
    lead.save()
    _send(client, staff, lead)
    assert mail.outbox == []
    lead.refresh_from_db()
    assert lead.email_status == "not_sent"


def test_a_passed_lead_cannot_be_sent(client, staff, settings):
    # The old mechanism set `passed` and believed that was a gate. Now it is one.
    settings.DEFAULT_FROM_EMAIL = "mail@anansiatlas.com"
    lead = _lead(status=SalesLead.Status.PASSED)
    _send(client, staff, lead)
    assert mail.outbox == []


def test_the_gate_names_the_reason():
    lead = _lead()
    lead.set_disposition(DispositionReason.WRONG_GEOGRAPHY)
    assert "Outside campaign geography" in lead.cold_outreach_block()


def test_an_eligible_lead_still_sends(client, staff, settings):
    # The gate must not become a blanket refusal.
    settings.DEFAULT_FROM_EMAIL = "mail@anansiatlas.com"
    lead = _lead()
    _send(client, staff, lead)
    assert len(mail.outbox) == 1


# ── audit trail ─────────────────────────────────────────────────────────────

def test_reason_code_and_detail_are_queryable():
    lead = _lead()
    lead.set_disposition(DispositionReason.ORGANIZATION_CLOSED,
                         detail="Site down, 990 shows final return",
                         source="human", evidence_as_of=dt.date(2026, 8, 12))
    lead.save()
    found = SalesLead.objects.filter(
        disposition=SalesLead.DISPOSITION_DISQUALIFIED,
        disposition_reason=DispositionReason.ORGANIZATION_CLOSED).first()
    assert found == lead
    assert found.disposition_source == "human"
    assert found.disposition_at is not None
    assert found.evidence_as_of == dt.date(2026, 8, 12)
    assert "final return" in found.disposition_detail


def test_campaign_disqualification_is_not_global_suppression():
    # "Wrong county for this campaign" must never become "never contact again".
    from openoutreach.signals.models import EmailOptOut

    lead = _lead()
    lead.set_disposition(DispositionReason.WRONG_GEOGRAPHY)
    lead.save()
    assert not EmailOptOut.objects.filter(email=lead.email).exists()


# ── history survives a later decision ───────────────────────────────────────

def test_existing_drafts_survive_a_later_disqualification():
    lead = _lead()
    msg = OutreachMessage.objects.create(
        lead=lead, subject="s", body="b", primary_angle=OutreachAngle.COUNTY_FUNDING)
    lead.set_disposition(DispositionReason.ORGANIZATION_CLOSED)
    lead.save()
    msg.refresh_from_db()
    # Preserved, not deleted; still drafted, not falsely marked sent.
    assert msg.body == "b"
    assert msg.status == OutreachMessage.Status.DRAFTED
    assert msg.primary_angle == OutreachAngle.COUNTY_FUNDING


def test_a_sent_message_is_not_rewritten_by_a_later_disqualification():
    lead = _lead()
    msg = OutreachMessage.objects.create(
        lead=lead, subject="s", body="b", status=OutreachMessage.Status.SENT)
    lead.set_disposition(DispositionReason.ORGANIZATION_CLOSED)
    lead.save()
    msg.refresh_from_db()
    assert msg.status == OutreachMessage.Status.SENT


# ── evidence vs commentary ──────────────────────────────────────────────────

def test_operator_notes_never_reach_the_writer_as_fact():
    lead = _lead(operator_notes="Probably struggling with staffing. Call Marcus first.")
    joined = " ".join(_lead_facts(lead))
    assert "staffing" not in joined
    assert "Call Marcus" not in joined


def test_legacy_mixed_notes_are_not_trusted_as_evidence():
    # Old rows hold research, archived emails and commentary in one blob. Nothing can
    # tell which sentence was which, so none of it is passed as fact.
    lead = _lead(notes="[archived opener] Hi Dana...\n\nMight know Malcolm. Probably short staffed.")
    joined = " ".join(_lead_facts(lead))
    assert "Malcolm" not in joined
    assert "archived opener" not in joined
    # But it is preserved, not destroyed.
    lead.refresh_from_db()
    assert "Malcolm" in lead.notes


def test_verified_research_does_reach_the_writer():
    lead = _lead(research_profile="Runs a 24-hour emergency youth shelter, ages 6-17.")
    joined = " ".join(_lead_facts(lead))
    assert "24-hour emergency youth shelter" in joined


def test_relationship_context_reaches_the_writer_but_in_its_own_channel():
    lead = _lead(relationship_context="Marcus worked with her at Aeras Foundation.")
    assert "Aeras" not in " ".join(_lead_facts(lead))       # not researched fact
    block = _relationship_block(lead)
    assert "Aeras" in block                                  # but the writer does get it
    assert "NOT researched fact" in block


def test_relationship_block_is_empty_when_there_is_no_relationship():
    assert _relationship_block(_lead()) == ""


# ── regression: existing safeguards ─────────────────────────────────────────

def test_opt_out_still_blocks(client, staff, settings):
    from openoutreach.signals.unsubscribe import record_opt_out

    settings.DEFAULT_FROM_EMAIL = "mail@anansiatlas.com"
    lead = _lead()
    record_opt_out(lead.email)
    _send(client, staff, lead)
    assert mail.outbox == []


def test_angle_tracking_still_works_through_the_gate(client, staff, settings):
    settings.DEFAULT_FROM_EMAIL = "mail@anansiatlas.com"
    lead = _lead()
    msg = OutreachMessage.objects.create(
        lead=lead, primary_angle=OutreachAngle.FREE_RESOURCE,
        status=OutreachMessage.Status.DRAFTED)
    _send(client, staff, lead)
    msg.refresh_from_db()
    assert msg.status == OutreachMessage.Status.SENT
    assert msg.primary_angle == OutreachAngle.FREE_RESOURCE
