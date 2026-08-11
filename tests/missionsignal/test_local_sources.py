"""State/county/city ingestion.

Network is mocked throughout — a suite that fetches orangecountyfl.net is a suite
that fails when someone else's web server has a bad morning. The one test that does
hit the network is opt-in via LOCAL_SOURCE_LIVE_CHECK=1.
"""
import os
from datetime import date

import pytest

from openoutreach.core.models import Organization, Project
from openoutreach.funding import local_sources as ls
from openoutreach.funding.models import Opportunity
from openoutreach.funding.web_discovery import WebDiscoveryLLMUnavailable

pytestmark = pytest.mark.django_db


def _project(state="Florida", county="Orange", city="Orlando"):
    org = Organization.objects.create(
        name="Test Youth Org", website="https://example-real-site.org",
        mission="STEM for girls", state=state, county=county, city=city,
    )
    return Project.objects.create(organization=org, name="Test", programs="Coding")


# --------------------------------------------------------------------------
# Geography matching
# --------------------------------------------------------------------------

def test_orlando_org_matches_state_county_and_city_sources():
    p = _project()
    keys = {s.key for s in ls.sources_for_organization(p.organization)}
    assert "occ-ccc-grants" in keys          # county
    assert "orlando-community-investment" in keys  # city


def test_a_different_county_does_not_get_orange_county_sources():
    p = _project(county="Miami-Dade", city="Miami")
    keys = {s.key for s in ls.sources_for_organization(p.organization)}
    assert not any(k.startswith("occ-") for k in keys)
    assert not any(k.startswith("orlando-") for k in keys)


def test_state_sources_still_apply_when_county_is_unknown():
    """An org that never told us its county should not lose state-level coverage."""
    p = _project(county="", city="")
    matched = ls.sources_for_organization(p.organization, include_blocked=True)
    assert any(s.level == ls.STATE for s in matched)


def test_an_org_with_no_state_matches_nothing():
    p = _project(state="", county="", city="")
    assert ls.sources_for_organization(p.organization) == []


def test_out_of_state_org_matches_nothing():
    p = _project(state="Georgia", county="Fulton", city="Atlanta")
    assert ls.sources_for_organization(p.organization) == []


# --------------------------------------------------------------------------
# Blocked sources
# --------------------------------------------------------------------------

def test_blocked_sources_are_excluded_from_fetching_but_still_reported():
    """FLDOE is unreachable, not nonexistent. It must never be silently dropped —
    it's the most relevant state program for an after-school provider."""
    p = _project()
    assert all(not s.is_blocked for s in ls.sources_for_organization(p.organization))
    with_blocked = ls.sources_for_organization(p.organization, include_blocked=True)
    assert any(s.key == "fl-doe-21cclc" and s.is_blocked for s in with_blocked)


def test_report_names_the_blocked_source_and_the_reason(monkeypatch):
    monkeypatch.setattr(ls, "fetch_page", lambda url: "Grant Funding page text")
    monkeypatch.setattr(ls, "extract_grant_programs",
                        lambda *a, **k: (_ for _ in ()).throw(WebDiscoveryLLMUnavailable("no key")))
    report = ls.discover_local_for_project(_project(), dry_run=True)
    assert any("21st Century" in b and "403" in b for b in report.blocked)


# --------------------------------------------------------------------------
# Extraction paths
# --------------------------------------------------------------------------

def test_page_level_fallback_carries_no_deadline(monkeypatch):
    """A date scraped off a 90k-char municipal page is as likely to be a council
    meeting as an application deadline. Wrong deadline > no deadline, in cost."""
    monkeypatch.setattr(ls, "fetch_page", lambda url: "x" * 5000)
    monkeypatch.setattr(ls, "extract_grant_programs",
                        lambda *a, **k: (_ for _ in ()).throw(WebDiscoveryLLMUnavailable("no key")))
    report = ls.discover_local_for_project(_project(), dry_run=True)
    assert report.extraction == "page-level"
    assert report.candidates
    assert all(c["deadline"] is None for c in report.candidates)


def test_llm_path_produces_one_candidate_per_extracted_program(monkeypatch):
    monkeypatch.setattr(ls, "fetch_page", lambda url: "page text")
    monkeypatch.setattr(ls, "extract_grant_programs", lambda *a, **k: [
        {"title": "Mini-Grant Funding", "description": "For youth programs.",
         "deadline": date(2027, 2, 28), "amount_text": "up to $10,000",
         "eligibility_text": "501(c)(3) under $300,000 budget", "confidence": "high"},
    ])
    report = ls.discover_local_for_project(_project(), dry_run=True)
    assert report.extraction == "programs"
    names = [c["name"] for c in report.candidates]
    assert "Mini-Grant Funding" in names
    hit = next(c for c in report.candidates if c["name"] == "Mini-Grant Funding")
    assert hit["deadline"] == date(2027, 2, 28)
    assert "up to $10,000" in hit["description"]
    assert "$300,000" in hit["description"]


def test_unreachable_source_is_recorded_not_swallowed(monkeypatch):
    monkeypatch.setattr(ls, "fetch_page", lambda url: None)
    report = ls.discover_local_for_project(_project(), dry_run=True)
    assert report.fetched == 0
    assert len(report.unreachable) == report.matched
    assert report.candidates == []


# --------------------------------------------------------------------------
# Persistence
# --------------------------------------------------------------------------

def test_saved_rows_are_government_sourced_and_flagged_for_review(monkeypatch):
    monkeypatch.setattr(ls, "fetch_page", lambda url: "page text")
    monkeypatch.setattr(ls, "extract_grant_programs",
                        lambda *a, **k: (_ for _ in ()).throw(WebDiscoveryLLMUnavailable("no key")))
    p = _project()
    report = ls.discover_local_for_project(p)
    assert report.saved > 0
    rows = Opportunity.objects.filter(project=p)
    assert rows.count() == report.saved
    for row in rows:
        assert row.source_type == Opportunity.SourceType.GOVERNMENT
        assert row.verification_status == Opportunity.VerificationStatus.NEEDS_REVIEW
        assert row.source_urls and row.source_urls[0].startswith("https://")


def test_rerunning_updates_rather_than_duplicating(monkeypatch):
    monkeypatch.setattr(ls, "fetch_page", lambda url: "page text")
    monkeypatch.setattr(ls, "extract_grant_programs",
                        lambda *a, **k: (_ for _ in ()).throw(WebDiscoveryLLMUnavailable("no key")))
    p = _project()
    first = ls.discover_local_for_project(p)
    ls.discover_local_for_project(p)
    assert Opportunity.objects.filter(project=p).count() == first.saved


def test_dry_run_writes_nothing(monkeypatch):
    monkeypatch.setattr(ls, "fetch_page", lambda url: "page text")
    monkeypatch.setattr(ls, "extract_grant_programs",
                        lambda *a, **k: (_ for _ in ()).throw(WebDiscoveryLLMUnavailable("no key")))
    p = _project()
    report = ls.discover_local_for_project(p, dry_run=True)
    assert report.candidates
    assert Opportunity.objects.filter(project=p).count() == 0


# --------------------------------------------------------------------------
# Registry hygiene
# --------------------------------------------------------------------------

def test_registry_keys_and_urls_are_unique():
    keys = [s.key for s in ls.LOCAL_SOURCES]
    urls = [s.url for s in ls.LOCAL_SOURCES]
    assert len(keys) == len(set(keys))
    assert len(urls) == len(set(urls))


def test_every_source_is_https_and_scoped_to_a_state():
    for s in ls.LOCAL_SOURCES:
        assert s.url.startswith("https://"), s.key
        assert s.state, s.key
        assert s.level in (ls.STATE, ls.COUNTY, ls.CITY), s.key


def test_county_and_city_sources_declare_their_jurisdiction():
    for s in ls.LOCAL_SOURCES:
        if s.level == ls.COUNTY:
            assert s.county, s.key
        if s.level == ls.CITY:
            assert s.city and s.county, s.key


def test_no_registered_url_is_a_placeholder_domain():
    from openoutreach.funding.grounding import is_reserved_domain
    for s in ls.LOCAL_SOURCES:
        assert not is_reserved_domain(s.url), s.key


@pytest.mark.skipif(
    os.environ.get("LOCAL_SOURCE_LIVE_CHECK") != "1",
    reason="hits real government sites; set LOCAL_SOURCE_LIVE_CHECK=1 to run",
)
def test_live_every_unblocked_source_still_serves_a_page():
    """Run periodically. Government sites reorganize and a registry of 404s is
    worse than no registry."""
    from openoutreach.funding.web_discovery import fetch_page
    dead = [s.key for s in ls.LOCAL_SOURCES if not s.is_blocked and not fetch_page(s.url)]
    assert not dead, f"registered sources no longer reachable: {dead}"
