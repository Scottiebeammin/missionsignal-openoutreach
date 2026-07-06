"""import_warm_drafts: load hand-written warm emails onto warm leads by exact
email match (cockpit shows Marcus's version, not the composed template). Safe —
no fuzzy matching, no lead creation, never overwrites a sent lead."""
import json

import pytest
from django.core.management import call_command

from openoutreach.signals.models import SalesLead

pytestmark = pytest.mark.django_db


def _write(tmp_path, records):
    p = tmp_path / "drafts.json"
    p.write_text(json.dumps(records))
    return str(p)


def test_loads_real_email_by_exact_match(tmp_path):
    lead = SalesLead.objects.create(
        name="Anjali Vaya", organization="United Against Poverty",
        email="avaya@uap.org", list_segment="warm", warmth="warm", email_status="not_sent",
    )
    data = _write(tmp_path, [{"org": "United Against Poverty", "contact": "Anjali Vaya",
                              "email": "avaya@uap.org", "subject": "Reconnecting — UAP",
                              "body": "Hi Anjali,\n\nIt's Marcus. Real hand-written email."}])
    call_command("import_warm_drafts", "--data", data)
    lead.refresh_from_db()
    assert lead.subject_line == "Reconnecting — UAP"
    assert "Real hand-written email." in lead.outreach_draft


def test_draft_for_shows_the_loaded_email_over_template(tmp_path):
    from openoutreach.signals.outreach import draft_for
    lead = SalesLead.objects.create(
        name="Anjali Vaya", organization="United Against Poverty", email="avaya@uap.org",
        list_segment="warm", warmth="warm", why_fit="we worked together",
    )
    data = _write(tmp_path, [{"org": "United Against Poverty", "contact": "Anjali Vaya",
                              "email": "avaya@uap.org", "subject": "S",
                              "body": "MY REAL EMAIL BODY"}])
    call_command("import_warm_drafts", "--data", data)
    lead.refresh_from_db()
    _subject, body = draft_for(lead)
    assert body == "MY REAL EMAIL BODY"          # the loaded draft wins over the composed template
    assert "It's Marcus" not in body


def test_unmatched_email_is_not_loaded_and_no_lead_created(tmp_path):
    SalesLead.objects.create(name="A", organization="Org A", email="a@org.org",
                             list_segment="warm", warmth="warm")
    data = _write(tmp_path, [{"org": "Nowhere Inc", "contact": "Nobody",
                              "email": "ghost@nowhere.org", "subject": "S", "body": "B"}])
    before = SalesLead.objects.count()
    call_command("import_warm_drafts", "--data", data)
    assert SalesLead.objects.count() == before        # nothing created
    assert not SalesLead.objects.filter(email="ghost@nowhere.org").exists()


def test_never_overwrites_a_sent_lead(tmp_path):
    lead = SalesLead.objects.create(name="A", organization="Org A", email="a@org.org",
                                    list_segment="warm", warmth="warm",
                                    outreach_draft="ALREADY SENT VERSION", email_status="sent")
    data = _write(tmp_path, [{"org": "Org A", "contact": "A", "email": "a@org.org",
                              "subject": "new", "body": "NEW BODY"}])
    call_command("import_warm_drafts", "--data", data)
    lead.refresh_from_db()
    assert lead.outreach_draft == "ALREADY SENT VERSION"
