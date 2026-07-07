"""import_warm_batch: load the warm network from a committed JSON, self-contained
(no warm-list CSV needed). Idempotent; never overwrites a sent lead; never
downgrades pipeline status."""
import json

import pytest
from django.core.management import call_command

from openoutreach.signals.models import SalesLead

pytestmark = pytest.mark.django_db


def _write(tmp_path, rows):
    p = tmp_path / "warm.json"
    p.write_text(json.dumps(rows))
    return str(p)


ROWS = [{
    "organization": "United Against Poverty", "email": "avaya@uap.org",
    "name": "Anjali Vaya", "role": "ED", "phone": "", "warmth": "hot",
    "focus_area": "poverty", "why_fit": "we worked together", "subject_line": "Reconnecting",
    "outreach_draft": "Hi Anjali,\n\nIt's Marcus. My real hand-written email.",
    "cc_emails": "board@uap.org", "source": "warm", "status": "new", "email_status": "not_sent",
}]


def test_creates_warm_lead_with_draft_and_cc(tmp_path):
    call_command("import_warm_batch", "--data", _write(tmp_path, ROWS))
    lead = SalesLead.objects.get(list_segment="warm", email="avaya@uap.org")
    assert lead.name == "Anjali Vaya"
    assert lead.warmth == "hot"
    assert "My real hand-written email." in lead.outreach_draft
    assert lead.cc_emails == "board@uap.org"


def test_idempotent_no_duplicates(tmp_path):
    data = _write(tmp_path, ROWS)
    call_command("import_warm_batch", "--data", data)
    call_command("import_warm_batch", "--data", data)
    assert SalesLead.objects.filter(list_segment="warm", email="avaya@uap.org").count() == 1


def test_never_overwrites_a_sent_lead(tmp_path):
    SalesLead.objects.create(organization="UAP", email="avaya@uap.org", list_segment="warm",
                             name="Original", outreach_draft="ALREADY SENT", email_status="sent")
    call_command("import_warm_batch", "--data", _write(tmp_path, ROWS))
    lead = SalesLead.objects.get(email="avaya@uap.org")
    assert lead.outreach_draft == "ALREADY SENT"      # not clobbered
    assert lead.name == "Original"


def test_does_not_downgrade_existing_status(tmp_path):
    # A lead already advanced in the pipeline keeps its stage; only content refreshes.
    SalesLead.objects.create(organization="UAP", email="avaya@uap.org", list_segment="warm",
                             name="Old", status="call_done", email_status="not_sent")
    call_command("import_warm_batch", "--data", _write(tmp_path, ROWS))
    lead = SalesLead.objects.get(email="avaya@uap.org")
    assert lead.status == "call_done"                 # NOT downgraded to "new"
    assert lead.name == "Anjali Vaya"                 # content did refresh


def test_skips_rows_without_email(tmp_path):
    rows = [{**ROWS[0], "email": ""}]
    call_command("import_warm_batch", "--data", _write(tmp_path, rows))
    assert SalesLead.objects.filter(list_segment="warm").count() == 0
