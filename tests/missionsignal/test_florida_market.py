"""Florida Market Database: importer idempotency, promote-to-pipeline, views."""

import csv

import pytest
from django.contrib.auth.models import User
from django.core.management import call_command
from django.urls import reverse

from openoutreach.signals.market import promote_org_to_pipeline
from openoutreach.signals.models import CountyRollout, FloridaOrg, SalesLead

pytestmark = pytest.mark.django_db

MASTER_HEADERS = [
    "Record ID", "EIN", "Organization", "Sort Name", "Street", "City",
    "County", "Region", "State", "ZIP", "Subsection", "NTEE Code",
    "NTEE Sector", "Ruling Month", "Asset Amount", "Income Amount",
    "Priority", "Relationship Stage", "Next Action",
]
COUNTY_HEADERS = [
    "County", "Rollout Tier", "Region", "Owner", "Status",
    "IRS Nonprofit Count", "High-Priority Count", "Funder Starter Count",
    "Build Notes",
]


def _write(path, headers, rows):
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=headers)
        w.writeheader()
        for r in rows:
            w.writerow({h: r.get(h, "") for h in headers})
    return str(path)


def _fixture_csvs(tmp_path, asset_override=None):
    master = _write(tmp_path / "master.csv", MASTER_HEADERS, [
        {
            "Record ID": "NP-000001", "EIN": "111111111",
            "Organization": "Sunshine Youth Org", "City": "Miami",
            "County": "Miami-Dade", "Region": "South Florida", "State": "FL",
            "ZIP": "33101", "NTEE Sector": "Youth Development",
            "NTEE Code": "O50",
            "Asset Amount": asset_override or "500000", "Income Amount": "120000",
            "Priority": "High", "Relationship Stage": "New",
            "Next Action": "Call them",
        },
        {
            "Record ID": "NP-000002", "EIN": "222222222",
            "Organization": "Gulf Coast Arts", "City": "Tampa",
            "County": "Hillsborough", "Region": "Tampa Bay", "State": "FL",
            "NTEE Sector": "Arts & Culture",
            "Asset Amount": "", "Income Amount": "",
        },
    ])
    counties = _write(tmp_path / "counties.csv", COUNTY_HEADERS, [
        {
            "County": "Miami-Dade", "Rollout Tier": "Priority 1",
            "Region": "South Florida", "Owner": "Scott",
            "Status": "Not started", "IRS Nonprofit Count": "12000",
            "High-Priority Count": "900", "Funder Starter Count": "5",
            "Build Notes": "Start here",
        },
        {
            "County": "Hillsborough", "Rollout Tier": "Priority 2",
            "Region": "Tampa Bay", "Owner": "Research queue",
            "Status": "Not started", "IRS Nonprofit Count": "6000",
            "High-Priority Count": "400",
            "Funder Starter Count": '=COUNTIF(Funders!D$5:D$28,"*"&A5&"*")',
            "Build Notes": "",
        },
    ])
    return master, counties


def _import(master, counties):
    call_command("import_florida_market", master=master, counties=counties)


def _staff_client(client):
    User.objects.create_user(username="admin", password="pw", is_staff=True)
    client.login(username="admin", password="pw")
    return client


# ── Importer ─────────────────────────────────────────────────────────────────

def test_import_creates_orgs_and_counties(tmp_path):
    master, counties = _fixture_csvs(tmp_path)
    _import(master, counties)
    assert FloridaOrg.objects.count() == 2
    assert CountyRollout.objects.count() == 2

    org = FloridaOrg.objects.get(record_id="NP-000001")
    assert org.asset_amount == 500000
    assert org.income_amount == 120000
    assert org.county == "Miami-Dade"

    blank = FloridaOrg.objects.get(record_id="NP-000002")
    assert blank.asset_amount is None and blank.income_amount is None

    hb = CountyRollout.objects.get(county="Hillsborough")
    assert hb.nonprofit_count == 6000
    assert hb.funder_starter_count == 0  # spreadsheet formula → 0


def test_import_is_idempotent_and_updates(tmp_path):
    master, counties = _fixture_csvs(tmp_path)
    _import(master, counties)
    _import(master, counties)  # re-run: no duplicates
    assert FloridaOrg.objects.count() == 2
    assert CountyRollout.objects.count() == 2

    # Changed value updates in place; promoted_lead untouched.
    org = FloridaOrg.objects.get(record_id="NP-000001")
    lead, _ = promote_org_to_pipeline(org)
    master2, counties2 = _fixture_csvs(tmp_path, asset_override="750000")
    _import(master2, counties2)
    org.refresh_from_db()
    assert org.asset_amount == 750000
    assert org.promoted_lead_id == lead.id
    assert FloridaOrg.objects.count() == 2


# ── Promote to pipeline ──────────────────────────────────────────────────────

def test_promote_creates_segmented_lead_once(tmp_path, client):
    master, counties = _fixture_csvs(tmp_path)
    _import(master, counties)
    _staff_client(client)
    org = FloridaOrg.objects.get(record_id="NP-000001")

    url = reverse("operator-market-promote", args=[org.pk])
    resp = client.post(url, HTTP_HOST="localhost")
    assert resp.status_code == 302
    org.refresh_from_db()
    lead = org.promoted_lead
    assert lead is not None
    assert lead.name == "Sunshine Youth Org"
    assert lead.organization == "Sunshine Youth Org"
    assert lead.source == SalesLead.Source.COLD
    assert lead.status == SalesLead.Status.NEW
    assert lead.list_segment == SalesLead.Segment.COLD_FLORIDA_CRM
    assert lead.warmth == SalesLead.Warmth.COLD
    assert lead.region == "Miami-Dade"
    assert "111111111" in lead.notes and "O50" in lead.notes and "500,000" in lead.notes

    # Second click doesn't duplicate.
    client.post(url, HTTP_HOST="localhost")
    assert SalesLead.objects.count() == 1
    org.refresh_from_db()
    assert org.promoted_lead_id == lead.id


# ── Views ────────────────────────────────────────────────────────────────────

def test_market_page_filters_and_pagination(tmp_path, client):
    master, counties = _fixture_csvs(tmp_path)
    _import(master, counties)
    _staff_client(client)

    resp = client.get(reverse("operator-market"), HTTP_HOST="localhost")
    assert resp.status_code == 200
    assert b"Sunshine Youth Org" in resp.content
    assert b"Gulf Coast Arts" in resp.content

    resp = client.get(
        reverse("operator-market"),
        {"county": "Miami-Dade", "min_assets": "100000", "q": "Sunshine", "page": "1"},
        HTTP_HOST="localhost",
    )
    assert resp.status_code == 200
    assert b"Sunshine Youth Org" in resp.content
    assert b"Gulf Coast Arts" not in resp.content

    # NTEE sector filter
    resp = client.get(
        reverse("operator-market"), {"sector": "Arts & Culture"}, HTTP_HOST="localhost"
    )
    assert resp.status_code == 200
    assert b"Gulf Coast Arts" in resp.content
    assert b"Sunshine Youth Org" not in resp.content


def test_counties_page(tmp_path, client):
    master, counties = _fixture_csvs(tmp_path)
    _import(master, counties)
    _staff_client(client)

    resp = client.get(reverse("operator-market-counties"), HTTP_HOST="localhost")
    assert resp.status_code == 200
    assert b"Miami-Dade" in resp.content
    assert b"Priority 1" in resp.content

    resp = client.get(
        reverse("operator-market-counties"), {"sort": "nonprofits"}, HTTP_HOST="localhost"
    )
    assert resp.status_code == 200


# ── Contact enrichment (IRS 990-N e-Postcard) ────────────────────────────────

def _epostcard_zip(tmp_path, rows):
    """Build a fake data-download-epostcard.zip in tmp_path; return the dir."""
    import zipfile
    lines = "\n".join("|".join(r) for r in rows) + "\n"
    with zipfile.ZipFile(tmp_path / "data-download-epostcard.zip", "w") as zf:
        zf.writestr("data-download-epostcard.txt", lines)
    return str(tmp_path)


def _epostcard_row(ein, year, website, officer):
    return [ein, year, "SOME ORG", "T", "F", "01-01", "12-31",
            website, officer, "1 Main St", "", "Miami", "", "FL", "33101", "US",
            "1 Main St", "", "Miami", "", "FL", "33101", "US", "", "", ""]


def test_enrich_joins_by_ein_and_keeps_newest_year(tmp_path):
    master, counties = _fixture_csvs(tmp_path)
    _import(master, counties)
    # DB EIN has no leading zeros here; file EIN zero-padded — join must normalize.
    irs_dir = _epostcard_zip(tmp_path, [
        _epostcard_row("0111111111", "2022", "www.old.org", "Old Officer"),
        _epostcard_row("111111111", "2024", "www.sunshineyouth.org", "Jane Doe"),
        _epostcard_row("222222222", "2023", "gulf@arts.org", "Bob Lee"),
        _epostcard_row("999999999", "2024", "www.nomatch.org", "Nobody"),
    ])
    call_command("enrich_florida_contacts", irs_dir=irs_dir)

    org = FloridaOrg.objects.get(record_id="NP-000001")
    assert org.website == "http://www.sunshineyouth.org"  # newest year wins
    assert org.principal_officer == "Jane Doe"
    assert org.contact_source == "irs-epostcard-2024"
    assert org.contact_updated_at is not None

    arts = FloridaOrg.objects.get(record_id="NP-000002")
    assert arts.contact_email == "gulf@arts.org"  # '@' routes to email
    assert arts.website == ""
    assert arts.principal_officer == "Bob Lee"


def test_enrich_never_overwrites_other_source_without_force(tmp_path):
    master, counties = _fixture_csvs(tmp_path)
    _import(master, counties)
    org = FloridaOrg.objects.get(record_id="NP-000001")
    org.website = "https://manual.example.org"
    org.contact_source = "manual-research"
    org.save()

    irs_dir = _epostcard_zip(tmp_path, [
        _epostcard_row("111111111", "2024", "www.sunshineyouth.org", "Jane Doe"),
    ])
    call_command("enrich_florida_contacts", irs_dir=irs_dir)
    org.refresh_from_db()
    assert org.website == "https://manual.example.org"  # protected
    assert org.principal_officer == "Jane Doe"  # empty field still fills

    call_command("enrich_florida_contacts", irs_dir=irs_dir, force=True)
    org.refresh_from_db()
    assert org.website == "http://www.sunshineyouth.org"


def test_import_maps_priority_fields(tmp_path):
    master, counties = _fixture_csvs(tmp_path)
    _import(master, counties)
    org = FloridaOrg.objects.get(record_id="NP-000001")
    assert org.priority == "High"
    assert org.relationship_stage == "New"
    assert org.next_action == "Call them"


def test_promotion_carries_contact_info(tmp_path):
    master, counties = _fixture_csvs(tmp_path)
    _import(master, counties)
    org = FloridaOrg.objects.get(record_id="NP-000001")
    org.website = "https://sunshineyouth.org"
    org.phone = "305-555-0100"
    org.contact_email = "info@sunshineyouth.org"
    org.principal_officer = "Jane Doe"
    org.contact_source = "irs-epostcard-2024"
    org.save()

    lead, created = promote_org_to_pipeline(org)
    assert created
    assert lead.phone == "305-555-0100"
    assert lead.email == "info@sunshineyouth.org"
    assert "https://sunshineyouth.org" in lead.notes
    assert "Jane Doe" in lead.notes


def test_market_page_contact_and_priority_filters(tmp_path, client):
    master, counties = _fixture_csvs(tmp_path)
    _import(master, counties)
    org = FloridaOrg.objects.get(record_id="NP-000001")
    org.website = "https://sunshineyouth.org"
    org.save()
    _staff_client(client)

    resp = client.get(
        reverse("operator-market"), {"has_contact": "1"}, HTTP_HOST="localhost"
    )
    assert resp.status_code == 200
    assert b"Sunshine Youth Org" in resp.content
    assert b"Gulf Coast Arts" not in resp.content
    assert b"sunshineyouth.org" in resp.content

    resp = client.get(
        reverse("operator-market"), {"priority": "High"}, HTTP_HOST="localhost"
    )
    assert resp.status_code == 200
    assert b"Sunshine Youth Org" in resp.content
    assert b"Gulf Coast Arts" not in resp.content
