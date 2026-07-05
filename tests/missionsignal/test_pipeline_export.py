"""Canonical pipeline CSV export (n8n feed).

PII endpoint: emits lead emails, so it's gated — staff by session, or the
X-Pipeline-Token header matching PIPELINE_EXPORT_TOKEN. Emits the exact
canonical column contract the n8n composer parses.
"""
import csv
import io
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from openoutreach.signals.models import SalesLead
from openoutreach.signals.pipeline_export import CANON

pytestmark = pytest.mark.django_db


@pytest.fixture
def lead(db):
    return SalesLead.objects.create(
        name="Dana Reed",
        organization="Bright Paths",
        email="dana@brightpaths.org",
        role="Executive Director",
        list_segment="warm",
        warmth="hot",
        focus_area="Youth Development",
        why_fit="Central Florida youth org",
        subject_line="Thought of Bright Paths",
        source="warm-list",
    )


def test_export_forbidden_without_token(client, lead):
    response = client.get(reverse("pipeline-csv-export"))
    assert response.status_code == 403
    assert b"dana@brightpaths.org" not in response.content


def test_export_forbidden_with_wrong_token(client, lead):
    with patch.dict("os.environ", {"PIPELINE_EXPORT_TOKEN": "right-secret"}):
        response = client.get(reverse("pipeline-csv-export"), HTTP_X_PIPELINE_TOKEN="wrong-secret")
    assert response.status_code == 403


def test_export_ok_with_token_and_canonical_contract(client, lead):
    with patch.dict("os.environ", {"PIPELINE_EXPORT_TOKEN": "right-secret"}):
        response = client.get(reverse("pipeline-csv-export"), HTTP_X_PIPELINE_TOKEN="right-secret")
    assert response.status_code == 200
    assert response["Content-Type"] == "text/csv"
    rows = list(csv.DictReader(io.StringIO(response.content.decode())))
    assert list(rows[0].keys()) == CANON  # exact column order the composer expects
    row = rows[0]
    assert row["email"] == "dana@brightpaths.org"
    assert row["dedup_key"] == "dana@brightpaths.org"
    assert row["lead_id"].startswith("AA-")
    assert row["is_warm"] == "TRUE"
    assert row["warmth"] == "hot"
    assert row["first_name"] == "Dana"
    assert row["last_name"] == "Reed"
    assert row["focus_angle"] == "Youth Development"
    assert row["email_status"] == "not_sent"


def test_export_ok_for_staff_session_without_token(client, lead):
    staff = get_user_model().objects.create_user(username="ops", password="x", is_staff=True)
    client.force_login(staff)
    response = client.get(reverse("pipeline-csv-export"))
    assert response.status_code == 200
    assert b"dana@brightpaths.org" in response.content


def test_cold_lead_maps_to_false_warm(client, lead):
    SalesLead.objects.create(
        name="Sam Cole", organization="Metro Coalition", email="sam@metro.org",
        list_segment="cold_florida_crm", warmth="cold",
    )
    with patch.dict("os.environ", {"PIPELINE_EXPORT_TOKEN": "s"}):
        response = client.get(reverse("pipeline-csv-export"), HTTP_X_PIPELINE_TOKEN="s")
    rows = {r["email"]: r for r in csv.DictReader(io.StringIO(response.content.decode()))}
    assert rows["sam@metro.org"]["is_warm"] == "FALSE"
    assert rows["sam@metro.org"]["list_segment"] == "cold_florida_crm"
