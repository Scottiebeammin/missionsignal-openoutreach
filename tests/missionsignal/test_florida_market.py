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


# ---- fetch_990_contacts (Phase 2: full 990 XML) ----------------------------

_990_XML = """<?xml version="1.0" encoding="utf-8"?>
<Return xmlns="http://www.irs.gov/efile" returnVersion="2023v5.0">
  <ReturnHeader>
    <ReturnTs>2024-05-01T12:00:00-05:00</ReturnTs>
    <TaxYr>2023</TaxYr>
    <Filer>
      <EIN>0111111111</EIN>
      <BusinessName><BusinessNameLine1Txt>SUNSHINE YOUTH ORG</BusinessNameLine1Txt></BusinessName>
      <PhoneNum>3055550100</PhoneNum>
    </Filer>
    <BusinessOfficerGrp>
      <PersonNm>Jane Doe</PersonNm>
      <PersonTitleTxt>PRESIDENT</PersonTitleTxt>
      <PhoneNum>3055550199</PhoneNum>
    </BusinessOfficerGrp>
    <PreparerPersonGrp><PhoneNum>9995550000</PhoneNum></PreparerPersonGrp>
  </ReturnHeader>
  <ReturnData>
    <IRS990>
      <WebsiteAddressTxt>www.sunshineyouth.org</WebsiteAddressTxt>
      <PrincipalOfficerNm>Jane Doe</PrincipalOfficerNm>
    </IRS990>
  </ReturnData>
</Return>
"""


def test_parse_990_xml_extracts_contact_fields():
    from openoutreach.signals.management.commands.fetch_990_contacts import parse_990_xml

    extract = parse_990_xml(_990_XML.encode())
    assert extract == {
        "ein": "111111111",  # leading zero normalized
        "tax_year": 2023,
        "website": "http://www.sunshineyouth.org",
        "phone": "3055550100",  # Filer phone, not preparer's
        "officer": "Jane Doe",
    }
    assert parse_990_xml(b"<not-xml") is None
    assert parse_990_xml(b"<Return><ReturnHeader/></Return>") is None  # no EIN


def test_fetch_990_no_overwrite_and_newest_year_wins(tmp_path):
    from openoutreach.signals.management.commands.fetch_990_contacts import apply_extract

    master, counties = _fixture_csvs(tmp_path)
    _import(master, counties)
    org = FloridaOrg.objects.get(record_id="NP-000001")
    org.website = "https://manual.example.org"
    org.contact_source = "manual-research"
    org.save()

    extract = {"ein": "111111111", "tax_year": 2023, "officer": "Jane Doe",
               "website": "http://www.sunshineyouth.org", "phone": "3055550100"}
    assert apply_extract(org, extract) is True
    assert org.website == "https://manual.example.org"  # different source protected
    assert org.phone == "3055550100"  # empty field fills
    assert org.principal_officer == "Jane Doe"
    assert org.contact_source == "irs-990-xml-2023"
    org.save()

    # Same family, older year: must not regress the phone.
    older = dict(extract, tax_year=2021, phone="1112223333")
    assert apply_extract(org, older) is False
    assert org.phone == "3055550100"

    # Same family, newer year: refresh allowed.
    newer = dict(extract, tax_year=2024, phone="7865550123")
    assert apply_extract(org, newer) is True
    assert org.phone == "7865550123"
    assert org.contact_source == "irs-990-xml-2024"

    # --force clobbers the manual website.
    assert apply_extract(org, dict(extract, tax_year=2024), force=True) is True
    assert org.website == "http://www.sunshineyouth.org"


# ── Data-cleanup normalizers ─────────────────────────────────────────────────

from openoutreach.signals.market import (  # noqa: E402
    clean_email, clean_phone, clean_website, clean_zip, compact_amount,
    smart_title, website_domain,
)


def test_clean_phone():
    assert clean_phone("4075551234") == "(407) 555-1234"
    assert clean_phone("407-555-1234") == "(407) 555-1234"
    assert clean_phone("(407) 555-1234") == "(407) 555-1234"
    assert clean_phone("14075551234") == "(407) 555-1234"
    assert clean_phone("+1 407 555 1234") == "(407) 555-1234"
    assert clean_phone("555-1234") == ""          # too short
    assert clean_phone("CALL US") == ""           # letters
    assert clean_phone("") == ""
    assert clean_phone(None) == ""


def test_clean_website():
    assert clean_website("WWW.EXAMPLE.ORG") == "https://www.example.org"
    assert clean_website("http://Example.org/Path") == "http://example.org/path"
    assert clean_website("example.org.") == "https://example.org"
    assert clean_website("  example.org  ") == "https://example.org"
    for junk in ("N/A", "NONE", "NA", "WWW", ".", "", None, "nodothere"):
        assert clean_website(junk) == ""
    assert clean_website("info@example.org") == ""   # email → caller routes
    assert clean_website("https://" + "a" * 500 + ".org") == ""  # too long
    # idempotent
    assert clean_website("https://www.example.org") == "https://www.example.org"


def test_clean_email():
    assert clean_email("Info@Example.ORG") == "info@example.org"
    assert clean_email(" info@example.org ") == "info@example.org"
    assert clean_email("not-an-email") == ""
    assert clean_email("WWW.EXAMPLE.ORG") == ""
    assert clean_email(None) == ""


def test_clean_zip():
    assert clean_zip("32334-0092") == "32334-0092"
    assert clean_zip("32801") == "32801"
    assert clean_zip("328010000") == "32801"        # zero-padded +4 dropped
    assert clean_zip("328011234") == "32801-1234"
    assert clean_zip("garbage") == "garbage"        # unrecoverable → raw
    assert clean_zip("") == ""


def test_smart_title():
    assert smart_title("SUNSHINE YOUTH ORG INC") == "Sunshine Youth Org Inc"
    assert smart_title("friends of the library") == "Friends of the Library"
    assert smart_title("MCDONALD FAMILY FOUNDATION") == "McDonald Family Foundation"
    assert smart_title("O'BRIEN CHARITABLE TRUST") == "O'Brien Charitable Trust"
    assert smart_title("YMCA OF CENTRAL FLORIDA") == "YMCA of Central Florida"
    assert smart_title("VFW POST 4287") == "VFW Post 4287"
    assert smart_title("AMVETS POST II") == "AMVETS Post II"
    # Mixed case untouched
    assert smart_title("Already Nice Name") == "Already Nice Name"
    assert smart_title("McDonald House") == "McDonald House"
    # Idempotent
    once = smart_title("BOYS AND GIRLS CLUB OF TAMPA INC")
    assert smart_title(once) == once
    assert smart_title("") == ""


def test_compact_amount_and_domain():
    assert compact_amount(None) == "—"
    assert compact_amount(0) == "$0"
    assert compact_amount(950) == "$950"
    assert compact_amount(1_200_000) == "$1.2M"
    assert compact_amount(3_000) == "$3K"
    assert compact_amount(2_000_000_000) == "$2B"
    assert website_domain("https://www.example.org/about") == "example.org"
    assert website_domain("") == ""


# ── clean_florida_data command ───────────────────────────────────────────────

def test_clean_florida_data_command_idempotent(tmp_path):
    master, counties = _fixture_csvs(tmp_path)
    _import(master, counties)
    org = FloridaOrg.objects.get(record_id="NP-000001")
    org.name = "SUNSHINE YOUTH ORG INC"
    org.city = "MIAMI"
    org.street = "123 MAIN ST"
    org.principal_officer = "JANE MCDONALD"
    org.phone = "4075551234"
    org.website = "WWW.SUNSHINE.ORG"
    org.contact_email = "Info@Sunshine.ORG"
    org.zip_code = "331010000"
    org.save()

    org2 = FloridaOrg.objects.get(record_id="NP-000002")
    org2.phone = "CALL US"
    org2.website = "hello@gulfarts.org"   # email in website field
    org2.contact_email = ""
    org2.save()

    lead = SalesLead.objects.create(
        name="Test", phone="8135550000", email="Big@Org.COM",
    )
    bad_lead = SalesLead.objects.create(name="Keep", phone="n/a", email="not-an-email")

    call_command("clean_florida_data")

    org.refresh_from_db()
    assert org.name == "Sunshine Youth Org Inc"
    assert org.city == "Miami"
    assert org.street == "123 Main St"
    assert org.principal_officer == "Jane McDonald"
    assert org.phone == "(407) 555-1234"
    assert org.website == "https://www.sunshine.org"
    assert org.contact_email == "info@sunshine.org"
    assert org.zip_code == "33101"

    org2.refresh_from_db()
    assert org2.phone == ""                       # garbage blanked on FloridaOrg
    assert org2.website == ""                     # moved out of website
    assert org2.contact_email == "hello@gulfarts.org"

    lead.refresh_from_db()
    assert lead.phone == "(813) 555-0000"
    assert lead.email == "big@org.com"
    bad_lead.refresh_from_db()
    assert bad_lead.phone == "n/a"                # never blanked on SalesLead
    assert bad_lead.email == "not-an-email"

    # Second run: zero changes.
    from openoutreach.signals.management.commands.clean_florida_data import (
        clean_lead, clean_org,
    )
    for o in FloridaOrg.objects.all():
        assert clean_org(o) == []
    for l in SalesLead.objects.all():
        assert clean_lead(l) == []


def test_clean_florida_data_dry_run_writes_nothing(tmp_path):
    master, counties = _fixture_csvs(tmp_path)
    _import(master, counties)
    org = FloridaOrg.objects.get(record_id="NP-000001")
    org.name = "SUNSHINE YOUTH ORG INC"
    org.save()
    call_command("clean_florida_data", "--dry-run")
    org.refresh_from_db()
    assert org.name == "SUNSHINE YOUTH ORG INC"


# ── Service-area facet ───────────────────────────────────────────────────────

from openoutreach.signals.market import derive_service_area  # noqa: E402


def test_derive_service_area_ntee_letters():
    assert derive_service_area("A65", "", "Anything") == "Arts & Culture"
    assert derive_service_area("B25", "", "X") == "Education"
    assert derive_service_area("D20", "", "X") == "Environment & Animals"
    assert derive_service_area("F32", "", "X") == "Health & Mental Health"
    assert derive_service_area("K31", "", "X") == "Food Security"
    assert derive_service_area("L41", "", "X") == "Homelessness & Housing"
    assert derive_service_area("O50", "", "X") == "Youth Development"
    assert derive_service_area("X20", "", "X") == "Faith-Based"
    assert derive_service_area("s80", "", "X") == "Community & Civic"  # case-insensitive


def test_derive_service_area_name_fallback():
    assert derive_service_area("", "", "First Baptist Church of Ocala") == "Faith-Based"
    assert derive_service_area("", "Unknown / unclassified", "VFW Post 4287") == "Veterans"
    assert derive_service_area("Z99", "", "American Legion Post 12") == "Veterans"
    assert derive_service_area("", "", "Boys and Girls Club") == "Youth Development"
    assert derive_service_area("", "", "Community Food Pantry") == "Food Security"
    assert derive_service_area("", "", "Sunrise Housing Partners") == "Homelessness & Housing"
    assert derive_service_area("", "", "Riverside Widget Society") == "Unknown"


def test_clean_command_populates_service_area_and_filter(tmp_path, client):
    master, counties = _fixture_csvs(tmp_path)
    _import(master, counties)
    call_command("clean_florida_data")

    org = FloridaOrg.objects.get(record_id="NP-000001")  # NTEE O50
    assert org.service_area == "Youth Development"
    org2 = FloridaOrg.objects.get(record_id="NP-000002")  # no code, "Gulf Coast Arts"
    assert org2.service_area == "Arts & Culture"

    _staff_client(client)
    resp = client.get(
        reverse("operator-market"), {"serves": "Youth Development"}, HTTP_HOST="localhost"
    )
    assert resp.status_code == 200
    assert b"Sunshine Youth Org" in resp.content
    assert b"Gulf Coast Arts" not in resp.content
