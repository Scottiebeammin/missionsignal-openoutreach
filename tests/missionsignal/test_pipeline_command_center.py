"""Segmented sales-pipeline command center: importer reconcile rules + views."""

import csv

import pytest
from django.contrib.auth.models import User
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from openoutreach.signals.models import SalesLead

pytestmark = pytest.mark.django_db


# ── Helpers ──────────────────────────────────────────────────────────────────

CANONICAL_HEADERS = [
    "lead_id", "dedup_key", "is_warm", "list_segment", "warmth",
    "campaign_track", "ref", "organization", "contact_name", "first_name",
    "last_name", "role_title", "email", "relationship_depth", "focus_angle",
    "subject_line", "stage", "next_action", "why_fit", "website",
    "email_status", "source", "date_added", "last_updated", "notes", "region",
]


def _write_csv(tmp_path, rows, headers=None):
    path = tmp_path / "pipeline.csv"
    headers = headers or CANONICAL_HEADERS
    with open(path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({h: row.get(h, "") for h in headers})
    return str(path)


def _row(**overrides):
    base = {
        "is_warm": "FALSE",
        "list_segment": "cold_florida_crm",
        "warmth": "cold",
        "organization": "Sunshine Youth Org",
        "contact_name": "Jane Doe",
        "role_title": "Executive Director",
        "email": "jane@sunshine.org",
        "stage": "Not started",
        "email_status": "not_sent",
        "region": "Miami-Dade",
        "why_fit": "Runs youth programs",
    }
    base.update(overrides)
    return base


def _staff_client(client):
    User.objects.create_user(username="opstaff", password="pw", is_staff=True)
    client.login(username="opstaff", password="pw")
    return client


# ── Importer ──────────────────────────────────────────────────────────────────

def test_import_creates_cold_lead(tmp_path):
    call_command("import_pipeline_csv", _write_csv(tmp_path, [_row()]))
    lead = SalesLead.objects.get(email="jane@sunshine.org")
    assert lead.source == SalesLead.Source.COLD
    assert lead.list_segment == SalesLead.Segment.COLD_FLORIDA_CRM
    assert lead.warmth == "cold"
    assert lead.region == "Miami-Dade"
    assert lead.role == "Executive Director"
    assert lead.status == SalesLead.Status.NEW
    assert "Runs youth programs" in lead.why_fit


def test_import_upserts_by_email_no_duplicates(tmp_path):
    call_command("import_pipeline_csv", _write_csv(tmp_path, [_row()]))
    call_command("import_pipeline_csv", _write_csv(
        tmp_path, [_row(email="JANE@Sunshine.org", region="Broward")]))
    assert SalesLead.objects.filter(email__iexact="jane@sunshine.org").count() == 1
    assert SalesLead.objects.get(email__iexact="jane@sunshine.org").region == "Broward"


def test_import_warm_wins_never_flips_to_cold(tmp_path):
    SalesLead.objects.create(
        name="Jane Doe", email="jane@sunshine.org",
        source=SalesLead.Source.WARM, list_segment=SalesLead.Segment.WARM,
    )
    call_command("import_pipeline_csv", _write_csv(tmp_path, [_row(is_warm="FALSE")]))
    lead = SalesLead.objects.get(email="jane@sunshine.org")
    assert lead.source == SalesLead.Source.WARM
    assert lead.list_segment == SalesLead.Segment.WARM


def test_import_is_warm_true_maps_warm(tmp_path):
    call_command("import_pipeline_csv", _write_csv(
        tmp_path, [_row(is_warm="TRUE", list_segment="warm", warmth="hot")]))
    lead = SalesLead.objects.get(email="jane@sunshine.org")
    assert lead.source == SalesLead.Source.WARM
    assert lead.list_segment == SalesLead.Segment.WARM
    assert lead.warmth == "hot"


def test_import_never_downgrades_worked_status(tmp_path):
    SalesLead.objects.create(
        name="Jane Doe", email="jane@sunshine.org",
        status=SalesLead.Status.CALL_SCHEDULED,
    )
    call_command("import_pipeline_csv", _write_csv(tmp_path, [_row(stage="Not started")]))
    assert SalesLead.objects.get(email="jane@sunshine.org").status == SalesLead.Status.CALL_SCHEDULED


def test_import_promotes_new_lead_stage(tmp_path):
    call_command("import_pipeline_csv", _write_csv(tmp_path, [_row(stage="Reached out")]))
    assert SalesLead.objects.get(email="jane@sunshine.org").status == SalesLead.Status.REACHED_OUT


def test_import_dry_run_writes_nothing(tmp_path):
    call_command("import_pipeline_csv", _write_csv(tmp_path, [_row()]), "--dry-run")
    assert SalesLead.objects.count() == 0


def test_import_unknown_columns_land_in_notes(tmp_path):
    headers = CANONICAL_HEADERS + ["mystery_col"]
    call_command("import_pipeline_csv", _write_csv(
        tmp_path, [_row(mystery_col="keep me")], headers=headers))
    assert "mystery_col: keep me" in SalesLead.objects.get(email="jane@sunshine.org").notes


# ── Pipeline view ─────────────────────────────────────────────────────────────

def test_pipeline_segment_filter_and_counts(client):
    _staff_client(client)
    SalesLead.objects.create(name="Warm One", email="w@x.org",
                             list_segment=SalesLead.Segment.WARM, warmth="hot")
    SalesLead.objects.create(name="Cold One", email="c@x.org",
                             source=SalesLead.Source.COLD,
                             list_segment=SalesLead.Segment.COLD_FLORIDA_CRM,
                             warmth="cold", region="Orlando")
    resp = client.get(reverse("operator-pipeline"), HTTP_HOST="localhost")
    assert resp.status_code == 200
    assert resp.context["segment_counts"] == {"warm": 1, "cold_florida_crm": 1}

    resp = client.get(reverse("operator-pipeline") + "?segment=cold_florida_crm",
                      HTTP_HOST="localhost")
    assert resp.status_code == 200
    leads = list(resp.context["leads"])
    assert [l.name for l in leads] == ["Cold One"]
    assert resp.context["segment_total"] == 1
    assert b"Orlando" in resp.content


def test_pipeline_sort_due_then_warmth(client):
    _staff_client(client)
    today = timezone.localdate()
    SalesLead.objects.create(name="B Hot", email="b@x.org", warmth="hot",
                             organization="Beta")
    SalesLead.objects.create(name="A Cold Due", email="a@x.org", warmth="cold",
                             organization="Alpha", next_follow_up=today)
    SalesLead.objects.create(name="C Warm", email="cw@x.org", warmth="warm",
                             organization="Gamma")
    resp = client.get(reverse("operator-pipeline"), HTTP_HOST="localhost")
    names = [l.name for l in resp.context["leads"]]
    assert names == ["A Cold Due", "B Hot", "C Warm"]
    assert resp.context["due_count"] == 1


def test_dashboard_pipeline_card_renders(client):
    _staff_client(client)
    SalesLead.objects.create(name="Warm One", email="w@x.org",
                             list_segment=SalesLead.Segment.WARM)
    resp = client.get(reverse("operator-dashboard"), HTTP_HOST="localhost")
    assert resp.status_code == 200
    assert b"Sales Pipeline" in resp.content
    assert resp.context["pipeline_summary"]["warm"] == 1
    assert resp.context["pipeline_summary"]["total"] == 1
