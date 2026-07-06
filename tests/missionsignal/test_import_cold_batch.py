"""import_cold_batch: load the curated cold batch from a committed JSON file,
self-contained (no FloridaOrg market table needed). Idempotent; never overwrites
a sent lead."""
import json

import pytest
from django.core.management import call_command

from openoutreach.signals.models import SalesLead

pytestmark = pytest.mark.django_db


def _write(tmp_path, batch):
    p = tmp_path / "cold.json"
    p.write_text(json.dumps(batch))
    return str(p)


BATCH = {
    "emailable": [{
        "organization": "Arnette House Inc", "email": "info@arnettehouse.org",
        "name": "Jane Officer", "role": "", "phone": "", "focus_area": "human services",
        "why_fit": "youth shelter", "subject_line": "S", "outreach_draft": "",
        "list_segment": "cold_florida_crm", "source": "cold",
    }],
    "call_list": [{
        "organization": "United Way Of Marion Co Inc", "email": "",
        "name": "", "role": "", "phone": "(352) 732-9696", "focus_area": "",
        "why_fit": "", "subject_line": "", "outreach_draft": "CALL SCRIPT: Hi, this is Marcus...",
        "list_segment": "cold_call_list", "source": "cold",
    }],
}


def test_creates_emailable_and_call_list_leads(tmp_path):
    call_command("import_cold_batch", "--data", _write(tmp_path, BATCH))
    emailable = SalesLead.objects.get(list_segment="cold_florida_crm")
    assert emailable.email == "info@arnettehouse.org"
    assert emailable.name == "Jane Officer"
    assert emailable.focus_area == "human services"
    call = SalesLead.objects.get(list_segment="cold_call_list")
    assert call.phone == "(352) 732-9696"
    assert "CALL SCRIPT" in call.outreach_draft      # the script rides on the lead


def test_idempotent_no_duplicates(tmp_path):
    data = _write(tmp_path, BATCH)
    call_command("import_cold_batch", "--data", data)
    call_command("import_cold_batch", "--data", data)
    assert SalesLead.objects.filter(list_segment="cold_florida_crm").count() == 1
    assert SalesLead.objects.filter(list_segment="cold_call_list").count() == 1


def test_never_overwrites_a_sent_lead(tmp_path):
    SalesLead.objects.create(organization="Arnette House Inc", email="info@arnettehouse.org",
                             list_segment="cold_florida_crm", name="Original",
                             outreach_draft="ALREADY SENT", email_status="sent")
    call_command("import_cold_batch", "--data", _write(tmp_path, BATCH))
    lead = SalesLead.objects.get(email="info@arnettehouse.org")
    assert lead.name == "Original"                    # not clobbered
    assert lead.outreach_draft == "ALREADY SENT"
