"""IRS 990-PF foundation grant intelligence: parser, dedup, derivation, org join."""

import pytest

from openoutreach.funding.foundation_intel import (
    derive_foundation_funders,
    focus_areas_from_purposes,
    parse_990pf_grants,
    store_grants,
)
from openoutreach.funding.models import FoundationGrantPaid, Funder
from openoutreach.signals.models import FloridaOrg

pytestmark = pytest.mark.django_db

BUNDLE_URL = "https://apps.irs.gov/pub/epostcard/990/xml/2024/2024_TEOS_XML_01A.zip"

# Namespaced, like real IRS e-file returns.
_990PF_XML = """<?xml version="1.0" encoding="utf-8"?>
<Return xmlns="http://www.irs.gov/efile" returnVersion="2023v5.0">
  <ReturnHeader>
    <ReturnTs>2024-05-01T12:00:00-05:00</ReturnTs>
    <TaxYr>2023</TaxYr>
    <ReturnTypeCd>990PF</ReturnTypeCd>
    <Filer>
      <EIN>012345678</EIN>
      <BusinessName><BusinessNameLine1Txt>SUNSHINE FAMILY FOUNDATION</BusinessNameLine1Txt></BusinessName>
      <USAddress>
        <AddressLine1Txt>1 OCEAN DR</AddressLine1Txt>
        <CityNm>MIAMI</CityNm>
        <StateAbbreviationCd>FL</StateAbbreviationCd>
        <ZIPCd>33101</ZIPCd>
      </USAddress>
    </Filer>
  </ReturnHeader>
  <ReturnData>
    <IRS990PF>
      <SupplementaryInformationGrp>
        <GrantOrContributionPdDurYrGrp>
          <RecipientBusinessName><BusinessNameLine1Txt>SUNSHINE YOUTH ORG, INC.</BusinessNameLine1Txt></RecipientBusinessName>
          <RecipientUSAddress>
            <CityNm>MIAMI</CityNm>
            <StateAbbreviationCd>FL</StateAbbreviationCd>
          </RecipientUSAddress>
          <RecipientEINTxt>111111111</RecipientEINTxt>
          <GrantOrContributionPurposeTxt>YOUTH MENTORING PROGRAMS</GrantOrContributionPurposeTxt>
          <Amt>25000</Amt>
        </GrantOrContributionPdDurYrGrp>
        <GrantOrContributionPdDurYrGrp>
          <RecipientPersonNm>JANE SCHOLAR</RecipientPersonNm>
          <RecipientUSAddress>
            <CityNm>ATLANTA</CityNm>
            <StateAbbreviationCd>GA</StateAbbreviationCd>
          </RecipientUSAddress>
          <GrantOrContributionPurposeTxt>COLLEGE SCHOLARSHIP</GrantOrContributionPurposeTxt>
          <Amt>5000</Amt>
        </GrantOrContributionPdDurYrGrp>
      </SupplementaryInformationGrp>
    </IRS990PF>
  </ReturnData>
</Return>
"""

# Non-namespaced variant, out-of-state filer with one FL and one TX recipient.
_990PF_XML_PLAIN = """<?xml version="1.0" encoding="utf-8"?>
<Return returnVersion="2023v5.0">
  <ReturnHeader>
    <TaxYr>2024</TaxYr>
    <ReturnTypeCd>990PF</ReturnTypeCd>
    <Filer>
      <EIN>98-7654321</EIN>
      <BusinessName>
        <BusinessNameLine1Txt>PEACH STATE</BusinessNameLine1Txt>
        <BusinessNameLine2Txt>TRUST</BusinessNameLine2Txt>
      </BusinessName>
      <USAddress><CityNm>ATLANTA</CityNm><StateAbbreviationCd>GA</StateAbbreviationCd></USAddress>
    </Filer>
  </ReturnHeader>
  <ReturnData>
    <IRS990PF>
      <SupplementaryInformationGrp>
        <GrantOrContributionPdDurYrGrp>
          <RecipientBusinessName><BusinessNameLine1Txt>GULF COAST ARTS</BusinessNameLine1Txt></RecipientBusinessName>
          <RecipientUSAddress><CityNm>TAMPA</CityNm><StateAbbreviationCd>FL</StateAbbreviationCd></RecipientUSAddress>
          <GrantOrContributionPurposeTxt>ARTS EDUCATION</GrantOrContributionPurposeTxt>
          <Amt>10000</Amt>
        </GrantOrContributionPdDurYrGrp>
        <GrantOrContributionPdDurYrGrp>
          <RecipientBusinessName><BusinessNameLine1Txt>LONE STAR FOOD BANK</BusinessNameLine1Txt></RecipientBusinessName>
          <RecipientUSAddress><CityNm>DALLAS</CityNm><StateAbbreviationCd>TX</StateAbbreviationCd></RecipientUSAddress>
          <GrantOrContributionPurposeTxt>FOOD SECURITY</GrantOrContributionPurposeTxt>
          <Amt>7500</Amt>
        </GrantOrContributionPdDurYrGrp>
      </SupplementaryInformationGrp>
    </IRS990PF>
  </ReturnData>
</Return>
"""

_990_NOT_PF = """<?xml version="1.0" encoding="utf-8"?>
<Return xmlns="http://www.irs.gov/efile">
  <ReturnHeader><TaxYr>2023</TaxYr><Filer><EIN>555555555</EIN></Filer></ReturnHeader>
  <ReturnData><IRS990><WebsiteAddressTxt>example.org</WebsiteAddressTxt></IRS990></ReturnData>
</Return>
"""


# ---- parser -----------------------------------------------------------------

def test_parse_990pf_grants_namespaced():
    parsed = parse_990pf_grants(_990PF_XML.encode())
    assert parsed is not None
    assert parsed["filer_ein"] == "012345678"
    assert parsed["filer_name"] == "SUNSHINE FAMILY FOUNDATION"
    assert parsed["filer_city"] == "MIAMI"
    assert parsed["filer_state"] == "FL"
    assert parsed["tax_year"] == "2023"
    assert len(parsed["grants"]) == 2

    org_grant, person_grant = parsed["grants"]
    assert org_grant["recipient_name"] == "SUNSHINE YOUTH ORG, INC."
    assert org_grant["recipient_ein"] == "111111111"
    assert org_grant["recipient_city"] == "MIAMI"
    assert org_grant["recipient_state"] == "FL"
    assert org_grant["amount"] == 25000
    assert org_grant["purpose"] == "YOUTH MENTORING PROGRAMS"
    assert person_grant["recipient_name"] == "JANE SCHOLAR"
    assert person_grant["recipient_state"] == "GA"
    assert person_grant["amount"] == 5000


def test_parse_990pf_grants_non_namespaced_and_rejections():
    parsed = parse_990pf_grants(_990PF_XML_PLAIN.encode())
    assert parsed is not None
    assert parsed["filer_ein"] == "987654321"  # dashes stripped, 9 digits
    assert parsed["filer_name"] == "PEACH STATE TRUST"  # two name lines joined
    assert parsed["filer_state"] == "GA"
    assert [g["recipient_state"] for g in parsed["grants"]] == ["FL", "TX"]

    assert parse_990pf_grants(b"<not-xml") is None            # not XML
    assert parse_990pf_grants(_990_NOT_PF.encode()) is None   # a 990, not a 990-PF
    assert parse_990pf_grants(                                # 990-PF without an EIN
        b"<Return><ReturnData><IRS990PF/></ReturnData></Return>") is None


# ---- storage: FL relevance + dedup idempotency --------------------------------

def test_store_grants_fl_filter_and_dedup_idempotency():
    fl_parsed = parse_990pf_grants(_990PF_XML.encode())
    ga_parsed = parse_990pf_grants(_990PF_XML_PLAIN.encode())

    # FL filer keeps ALL grants (even the GA scholarship); GA filer keeps FL only.
    assert store_grants(fl_parsed, BUNDLE_URL) == {"created": 2, "skipped": 0}
    assert store_grants(ga_parsed, BUNDLE_URL) == {"created": 1, "skipped": 0}
    assert FoundationGrantPaid.objects.count() == 3
    assert not FoundationGrantPaid.objects.filter(recipient_name__icontains="LONE STAR").exists()

    # Re-storing the same returns is a no-op (dedup_key), not a duplication.
    assert store_grants(fl_parsed, BUNDLE_URL) == {"created": 0, "skipped": 2}
    assert store_grants(ga_parsed, BUNDLE_URL) == {"created": 0, "skipped": 1}
    assert FoundationGrantPaid.objects.count() == 3

    row = FoundationGrantPaid.objects.get(recipient_name__startswith="SUNSHINE")
    assert row.source_url == BUNDLE_URL
    assert row.filer_ein == "012345678"
    assert row.tax_year == "2023"
    assert len(row.dedup_key) == 64


# ---- funder derivation ---------------------------------------------------------

def _seed_foundation(ein="012345678", name="SUNSHINE FAMILY FOUNDATION", n=3):
    purposes = ["YOUTH MENTORING PROGRAMS", "SCHOLARSHIPS FOR YOUTH", "SCHOOL SUPPLIES"]
    for i in range(n):
        FoundationGrantPaid.objects.create(
            filer_ein=ein, filer_name=name, filer_city="MIAMI", filer_state="FL",
            recipient_name=f"RECIPIENT {i}", recipient_city="MIAMI", recipient_state="FL",
            amount=10_000 * (i + 1), purpose=purposes[i % len(purposes)],
            tax_year=str(2022 + i), source_url=BUNDLE_URL, dedup_key=f"{ein}-{i}",
        )


def test_derive_foundation_funders_creates_verified_funder():
    _seed_foundation()
    # Below the >= 3 grants bar: must NOT become a Funder.
    FoundationGrantPaid.objects.create(
        filer_ein="099999999", filer_name="TINY TRUST", filer_state="FL",
        recipient_name="SOMEONE", recipient_state="FL", amount=100,
        tax_year="2024", source_url=BUNDLE_URL, dedup_key="tiny-1",
    )

    summary = derive_foundation_funders()
    assert summary == {"created": 1, "updated": 0, "considered": 1}

    funder = Funder.objects.get(name="Sunshine Family Foundation")
    assert funder.funder_type == Funder.FunderType.FAMILY_FOUNDATION
    assert funder.verification_status == Funder.VerificationStatus.VERIFIED
    assert funder.active is True
    assert funder.external_ids == [{"system": "irs-ein", "id": "012345678"}]
    assert funder.source_urls == [BUNDLE_URL]
    assert funder.geography[0] == "Florida"
    assert "Miami" in funder.geography
    assert "Youth Development" in funder.focus_areas
    assert "Education" in funder.focus_areas
    assert "Derived from IRS 990-PF filings: 3 grants, $60,000 total, years 2022-2024." in funder.notes
    assert "Recipient 2" in funder.notes  # top recipient by amount

    # Idempotent: a second derivation refreshes, never duplicates.
    summary = derive_foundation_funders()
    assert summary == {"created": 0, "updated": 1, "considered": 1}
    assert Funder.objects.filter(name="Sunshine Family Foundation").count() == 1
    assert Funder.objects.get(name="Sunshine Family Foundation").notes.count(
        "Derived from IRS 990-PF filings:") == 1


def test_derive_foundation_funders_never_clobbers_existing():
    _seed_foundation()
    existing = Funder.objects.create(
        name="Sunshine Family Foundation",  # matched by exact name (no ein on file)
        funder_type=Funder.FunderType.COMMUNITY_FOUNDATION,
        geography=["Miami-Dade County"],
        focus_areas=["Human Services"],
        notes="Program officer met at conference.",
        verification_status=Funder.VerificationStatus.REVIEWED,
    )

    summary = derive_foundation_funders()
    assert summary == {"created": 0, "updated": 1, "considered": 1}

    existing.refresh_from_db()
    assert Funder.objects.count() == 1
    # Human-edited fields untouched:
    assert existing.funder_type == Funder.FunderType.COMMUNITY_FOUNDATION
    assert existing.geography == ["Miami-Dade County"]
    assert existing.focus_areas == ["Human Services"]
    assert existing.verification_status == Funder.VerificationStatus.REVIEWED
    # Blanks filled + derived note appended after the human note:
    assert existing.notes.startswith("Program officer met at conference.")
    assert "Derived from IRS 990-PF filings: 3 grants" in existing.notes
    assert {"system": "irs-ein", "id": "012345678"} in existing.external_ids
    assert BUNDLE_URL in existing.source_urls


def test_focus_areas_from_purposes_word_boundaries():
    # 'art' must not fire on 'partner' / 'quarter'; frequency orders the areas.
    areas = focus_areas_from_purposes([
        "PARTNER SUPPORT FOR QUARTERLY GALA",   # no cause keywords
        "FOOD PANTRY OPERATIONS",
        "HUNGER RELIEF MEALS",
        "VETERANS HOUSING ASSISTANCE",
    ])
    assert areas[0] == "Food Security"
    assert "Veterans" in areas
    assert "Homelessness & Housing" in areas
    assert "Arts & Culture" not in areas


def test_derivation_falls_back_to_recipient_names_for_generic_purposes():
    for i, recipient in enumerate(
        ["SHRINERS HOSPITALS FOR CHILDREN", "MERCY HOSPITAL FUND", "CITY BALLET"]
    ):
        FoundationGrantPaid.objects.create(
            filer_ein="055555555", filer_name="QUIET GIVING TRUST", filer_state="FL",
            recipient_name=recipient, recipient_state="FL", amount=1000,
            purpose="GENERAL OPERATING SUPPORT",  # no cause keywords
            tax_year="2024", source_url=BUNDLE_URL, dedup_key=f"q-{i}",
        )
    derive_foundation_funders()
    funder = Funder.objects.get(name="Quiet Giving Trust")
    assert "Health & Mental Health" in funder.focus_areas  # from recipient names


# ---- grants_to_orgs_like join --------------------------------------------------

def test_grants_to_orgs_like_joins_normalized_names():
    FloridaOrg.objects.create(
        record_id="NP-000001", ein="111111111", name="Sunshine Youth Org",
        county="Miami-Dade", service_area="Youth Development", state="FL",
    )
    FloridaOrg.objects.create(
        record_id="NP-000002", ein="222222222", name="Gulf Coast Arts",
        county="Hillsborough", service_area="Arts & Culture", state="FL",
    )
    youth_grant = FoundationGrantPaid.objects.create(
        filer_ein="012345678", filer_name="SUNSHINE FAMILY FOUNDATION",
        filer_state="FL", recipient_name="THE SUNSHINE YOUTH ORG, INC.",
        recipient_state="FL", amount=25000, tax_year="2023",
        source_url=BUNDLE_URL, dedup_key="k1",
    )
    FoundationGrantPaid.objects.create(
        filer_ein="098765432", filer_name="PEACH STATE TRUST", filer_state="GA",
        recipient_name="GULF COAST ARTS", recipient_state="FL", amount=10000,
        tax_year="2024", source_url=BUNDLE_URL, dedup_key="k2",
    )
    FoundationGrantPaid.objects.create(
        filer_ein="098765432", filer_name="PEACH STATE TRUST", filer_state="GA",
        recipient_name="UNRELATED CHARITY", recipient_state="FL", amount=500,
        tax_year="2024", source_url=BUNDLE_URL, dedup_key="k3",
    )

    # 'THE SUNSHINE YOUTH ORG, INC.' joins 'Sunshine Youth Org' via normalization.
    youth = FoundationGrantPaid.grants_to_orgs_like("Youth Development")
    assert list(youth) == [youth_grant]

    arts = FoundationGrantPaid.grants_to_orgs_like("Arts & Culture")
    assert arts.count() == 1
    assert arts.first().recipient_name == "GULF COAST ARTS"

    # County narrows; a wrong county excludes.
    assert FoundationGrantPaid.grants_to_orgs_like(
        "Youth Development", county="Miami-Dade").count() == 1
    assert FoundationGrantPaid.grants_to_orgs_like(
        "Youth Development", county="Hillsborough").count() == 0
    # Unknown service area -> empty queryset, still chainable.
    assert FoundationGrantPaid.grants_to_orgs_like("Space Exploration").count() == 0
