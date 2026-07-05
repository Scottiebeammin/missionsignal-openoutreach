"""Layer 2 grounded web discovery — fetch-then-extract, gated persistence.

The whole point of `funding/web_discovery.py` is the inversion: pages are
fetched FIRST with stdlib HTTP, and the LLM only structures what is provably
in the fetched text. These tests mock the LLM boundary (`pydantic_ai.Agent` /
`run_agent_sync`) and the HTTP boundary (`_http_get` / `fetch_page`) — no real
network, no real model — and assert the grounding guarantee end to end:
every candidate carries the URL that was actually fetched.
"""
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command

from openoutreach.core.models import Organization, Project
from openoutreach.funding import web_discovery
from openoutreach.funding.exceptions import WebDiscoveryLLMUnavailable
from openoutreach.funding.models import Funder, Opportunity
from openoutreach.funding.web_discovery import (
    ExtractedProgram,
    ProgramList,
    discover_for_project,
    extract_grant_programs,
    fetch_page,
    find_grant_links,
    parse_deadline_text,
)

HOMEPAGE_URL = "https://brightfutures.org"
GRANTS_URL = "https://brightfutures.org/grants"
APPLY_URL = "https://brightfutures.org/apply"

HOMEPAGE_HTML = """
<html><head><title>Bright Futures Foundation</title>
<script>var tracking = "secret";</script>
<style>.x { color: red; }</style></head>
<body>
<h1>Bright Futures Foundation</h1>
<p>We support youth development across Central Florida.</p>
<ul>
<li><a href="/grants">Our Grant Programs</a></li>
<li><a href="/apply">How to Apply</a></li>
<li><a href="/about">About Us</a></li>
<li><a href="/news">Latest News</a></li>
<li><a href="https://other-site.org/grants">Partner grants elsewhere</a></li>
<li><a href="/guidelines.pdf">Grant Guidelines (PDF)</a></li>
<li><a href="mailto:info@brightfutures.org">Email our grants team</a></li>
</ul>
</body></html>
"""

GRANTS_PAGE_TEXT = (
    "# Our Grant Programs\n"
    "The Youth Opportunity Grant awards up to $25,000 to nonprofits serving "
    "Central Florida youth. Applications are due March 15, 2026.\n"
    "The Community Sparks Grant supports neighborhood projects on a rolling basis."
)


@pytest.fixture
def project(db):
    organization = Organization.objects.create(
        name="Bright Harbor Youth Alliance",
        website="https://brightharbor.org",
        mission="Youth development and workforce readiness in Central Florida.",
        organization_type="nonprofit",
        city="Orlando",
        county="Orange County",
        state="Florida",
        focus_areas=["Youth Opportunity"],
        beneficiaries=["youth"],
    )
    return Project.objects.create(
        organization=organization,
        name="Core Programs",
        programs="After-school mentoring and career readiness for youth.",
    )


@pytest.fixture
def funder(db):
    return Funder.objects.create(
        name="Bright Futures Foundation",
        funder_type=Funder.FunderType.FAMILY_FOUNDATION,
        website=HOMEPAGE_URL,
        source_urls=[HOMEPAGE_URL],
        focus_areas=["Youth Opportunity"],
        verification_status=Funder.VerificationStatus.VERIFIED,
        active=True,
    )


# ── fetch_page ───────────────────────────────────────────────────────────────

class TestFetchPage:
    def test_extracts_readable_text_and_links(self):
        with patch.object(
            web_discovery, "_http_get",
            return_value=(HOMEPAGE_HTML.encode(), "text/html; charset=utf-8", "utf-8"),
        ):
            text = fetch_page(HOMEPAGE_URL)
        assert text is not None
        assert "Bright Futures Foundation" in text
        assert "We support youth development" in text
        assert "[Our Grant Programs](/grants)" in text  # links survive as [text](href)
        assert "secret" not in text       # script stripped
        assert "color: red" not in text   # style stripped

    def test_rejects_non_html(self):
        with patch.object(
            web_discovery, "_http_get",
            return_value=(b"%PDF-1.4 fake", "application/pdf", "utf-8"),
        ):
            assert fetch_page("https://brightfutures.org/guide") is None

    def test_survives_network_failure(self):
        with patch.object(web_discovery, "_http_get", side_effect=OSError("boom")):
            assert fetch_page(HOMEPAGE_URL) is None

    def test_rejects_non_http_urls(self):
        assert fetch_page("ftp://brightfutures.org") is None
        assert fetch_page("") is None


# ── find_grant_links (deterministic, no LLM) ─────────────────────────────────

class TestFindGrantLinks:
    def test_picks_grantish_same_host_links_only(self):
        text = web_discovery._html_to_text(HOMEPAGE_HTML)
        links = find_grant_links(text, HOMEPAGE_URL)
        assert links == [GRANTS_URL, APPLY_URL]
        # not /about or /news (not grant-ish), not other-site.org (off-host),
        # not the PDF (non-HTML extension), not mailto.

    def test_respects_limit(self):
        text = "[grants](/grants) [apply](/apply) [funding](/funding) [rfp](/rfp)"
        assert len(find_grant_links(text, HOMEPAGE_URL, limit=3)) == 3

    def test_deduplicates_and_skips_self_link(self):
        text = "[Grants](/grants) [Grant programs](/grants/) [Home funding](/)"
        assert find_grant_links(text, HOMEPAGE_URL) == [GRANTS_URL]


# ── deadline parsing ─────────────────────────────────────────────────────────

class TestParseDeadlineText:
    @pytest.mark.parametrize("text,expected", [
        ("March 15, 2026", date(2026, 3, 15)),
        ("Applications due by March 15th, 2026.", date(2026, 3, 15)),
        ("15 March 2026", date(2026, 3, 15)),
        ("2026-03-15", date(2026, 3, 15)),
        ("03/15/2026", date(2026, 3, 15)),
        ("Rolling basis", None),
        ("Quarterly deadlines", None),
        ("February 30, 2026", None),  # not a real date
        ("", None),
    ])
    def test_common_formats(self, text, expected):
        assert parse_deadline_text(text) == expected


# ── extract_grant_programs (the LLM step, fully mocked) ──────────────────────

def _mock_llm(output):
    """Patch the LLM boundary. Returns (context managers entered by caller)."""
    fake_agent = MagicMock()
    patches = (
        patch("openoutreach.core.llm.get_llm_model", return_value=object()),
        patch("pydantic_ai.Agent", return_value=fake_agent),
        patch("openoutreach.core.llm.run_agent_sync",
              return_value=SimpleNamespace(output=output)),
    )
    return fake_agent, patches


class TestExtractGrantPrograms:
    def test_llm_receives_only_fetched_text_and_grounding_prompt(self):
        output = ProgramList(programs=[ExtractedProgram(
            title="Youth Opportunity Grant",
            description="Up to $25,000 for youth nonprofits.",
            deadline_text="March 15, 2026",
            amount_text="$25,000",
            confidence="high",
        )])
        fake_agent, (p1, p2, p3) = _mock_llm(output)
        with p1, p2 as agent_cls, p3:
            programs = extract_grant_programs(GRANTS_PAGE_TEXT, GRANTS_URL, "Org: Test")

        # The user prompt contains exactly the fetched page text — nothing else
        # is offered as a fact source.
        user_prompt = fake_agent.run.call_args[0][0]
        assert GRANTS_PAGE_TEXT in user_prompt
        assert "the only permitted source of facts" in user_prompt
        assert "Org: Test" in user_prompt
        # The system prompt carries the anti-hallucination contract, temp 0.
        kwargs = agent_cls.call_args.kwargs
        assert "Extract ONLY grant programs" in kwargs["system_prompt"]
        assert "Never infer" in kwargs["system_prompt"]
        assert kwargs["model_settings"]["temperature"] == 0

        assert len(programs) == 1
        program = programs[0]
        assert program["title"] == "Youth Opportunity Grant"
        assert program["deadline"] == date(2026, 3, 15)
        assert program["source_url"] == GRANTS_URL

    def test_llm_supplied_url_is_discarded(self):
        # A hostile/hallucinating model smuggles URL-ish fields into its output.
        # The extractor never reads them: source_url is always the fetched page.
        smuggled = SimpleNamespace(programs=[SimpleNamespace(
            title="Fake Mega Grant",
            description="Totally real.",
            deadline_text="", amount_text="", eligibility_text="",
            confidence="high",
            url="https://attacker.example.com/fake",
            source_url="https://attacker.example.com/fake",
        )])
        _, (p1, p2, p3) = _mock_llm(smuggled)
        with p1, p2, p3:
            programs = extract_grant_programs(GRANTS_PAGE_TEXT, GRANTS_URL, "")
        assert programs[0]["source_url"] == GRANTS_URL
        assert all("attacker" not in str(v) for v in programs[0].values())

    def test_ambiguous_deadline_kept_as_text_not_guessed(self):
        output = ProgramList(programs=[ExtractedProgram(
            title="Community Sparks Grant", description="Neighborhood projects.",
            deadline_text="Rolling basis",
        )])
        _, (p1, p2, p3) = _mock_llm(output)
        with p1, p2, p3:
            programs = extract_grant_programs(GRANTS_PAGE_TEXT, GRANTS_URL, "")
        assert programs[0]["deadline"] is None
        assert "Rolling basis" in programs[0]["description"]

    def test_empty_page_text_short_circuits_without_llm(self):
        with patch("openoutreach.core.llm.get_llm_model") as get_model:
            assert extract_grant_programs("", GRANTS_URL, "") == []
            assert extract_grant_programs("   ", GRANTS_URL, "") == []
        get_model.assert_not_called()

    def test_missing_llm_raises_typed_error(self):
        with patch("openoutreach.core.llm.get_llm_model",
                   side_effect=ValueError("LLM_API_KEY is not set in Site Configuration.")):
            with pytest.raises(WebDiscoveryLLMUnavailable):
                extract_grant_programs(GRANTS_PAGE_TEXT, GRANTS_URL, "")


# ── discover_for_project (orchestrator + grounding gate) ─────────────────────

def _fake_fetch_pages(pages: dict):
    def fake_fetch(url, timeout=12, max_bytes=400_000):
        return pages.get(url.rstrip("/"))
    return fake_fetch


def _fake_extract(page_text, page_url, org_profile):
    """One program per page. Includes a smuggled source_url to prove the
    orchestrator stamps the fetched URL regardless of extractor output."""
    return [{
        "title": f"Program on {page_url.rsplit('/', 1)[-1] or 'home'}",
        "description": "Extracted from fetched text.",
        "deadline": date(2026, 3, 15),
        "deadline_text": "March 15, 2026",
        "amount_text": "$25,000",
        "eligibility_text": "501(c)(3) nonprofits",
        "confidence": "high",
        "source_url": "https://attacker.example.com/fake",  # must be ignored
    }]


HOMEPAGE_TEXT = web_discovery._html_to_text(HOMEPAGE_HTML)
CANNED_PAGES = {
    HOMEPAGE_URL: HOMEPAGE_TEXT,
    GRANTS_URL: GRANTS_PAGE_TEXT,
    APPLY_URL: "# How to Apply\nSubmit a letter of inquiry by March 15, 2026.",
}


class TestDiscoverForProject:
    def test_candidates_carry_fetched_url_through_the_gate(self, project, funder):
        with patch.object(web_discovery, "_require_llm"), \
             patch.object(web_discovery, "fetch_page", side_effect=_fake_fetch_pages(CANNED_PAGES)), \
             patch.object(web_discovery, "extract_grant_programs", side_effect=_fake_extract), \
             patch("openoutreach.funding.grounding.is_reachable", return_value=True):
            report = discover_for_project(project)

        assert report.funders_scanned == 1
        assert report.pages_fetched == 3  # homepage + 2 grant sub-pages
        assert report.programs_extracted == 2  # grants + apply pages
        assert report.saved == 2
        assert report.rejected == 0

        opportunities = Opportunity.objects.filter(project=project)
        assert opportunities.count() == 2
        saved_urls = {tuple(o.source_urls) for o in opportunities}
        # Every saved row points at a page this run actually fetched — the
        # smuggled attacker URL from the extractor never survives.
        assert saved_urls == {(GRANTS_URL,), (APPLY_URL,)}
        for opp in opportunities:
            assert opp.external_id.startswith("webdiscovery:")
            assert opp.verification_status == Opportunity.VerificationStatus.NEEDS_REVIEW
            assert opp.source_type == Opportunity.SourceType.FUNDER
            assert opp.source_name == funder.name
            assert opp.opportunity_type == Opportunity.OpportunityType.GRANT
            assert opp.deadline == date(2026, 3, 15)
            assert "attacker" not in str(opp.source_urls)

    def test_reserved_domain_funder_is_never_fetched(self, project, db):
        Funder.objects.create(
            name="Hallucinated Fund", website="https://example.org", active=True,
        )
        fetch = MagicMock()
        with patch.object(web_discovery, "_require_llm"), \
             patch.object(web_discovery, "fetch_page", fetch):
            report = discover_for_project(project)
        fetch.assert_not_called()  # no usable homepage → skipped entirely
        assert report.funders_scanned == 0
        assert Opportunity.objects.count() == 0

    def test_empty_pages_produce_no_candidates(self, project, funder):
        with patch.object(web_discovery, "_require_llm"), \
             patch.object(web_discovery, "fetch_page", side_effect=_fake_fetch_pages(CANNED_PAGES)), \
             patch.object(web_discovery, "extract_grant_programs", return_value=[]):
            report = discover_for_project(project)
        assert report.programs_extracted == 0
        assert report.saved == 0
        assert report.candidates == []
        assert Opportunity.objects.count() == 0

    def test_llm_missing_skips_cleanly_before_any_fetch(self, project, funder):
        fetch = MagicMock()
        with patch("openoutreach.core.llm.get_llm_model",
                   side_effect=ValueError("LLM_API_KEY is not set")), \
             patch.object(web_discovery, "fetch_page", fetch):
            report = discover_for_project(project)
        assert report.skipped_llm_unavailable is True
        fetch.assert_not_called()
        assert report.saved == 0
        assert Opportunity.objects.count() == 0

    def test_dry_run_persists_nothing(self, project, funder):
        with patch.object(web_discovery, "_require_llm"), \
             patch.object(web_discovery, "fetch_page", side_effect=_fake_fetch_pages(CANNED_PAGES)), \
             patch.object(web_discovery, "extract_grant_programs", side_effect=_fake_extract):
            report = discover_for_project(project, dry_run=True)
        assert report.programs_extracted == 2
        assert len(report.candidates) == 2
        assert {c["source_url"] for c in report.candidates} == {GRANTS_URL, APPLY_URL}
        assert report.saved == 0
        assert Opportunity.objects.count() == 0

    def test_unreachable_homepage_survives(self, project, funder):
        with patch.object(web_discovery, "_require_llm"), \
             patch.object(web_discovery, "fetch_page", return_value=None):
            report = discover_for_project(project)
        assert report.funders_scanned == 1
        assert report.pages_fetched == 0
        assert report.saved == 0
        assert any("unreachable" in line for line in report.lines)


# ── management command ───────────────────────────────────────────────────────

class TestDiscoverGrantPagesCommand:
    def test_dry_run_prints_programs_and_persists_nothing(self, project, funder, capsys):
        with patch.object(web_discovery, "_require_llm"), \
             patch.object(web_discovery, "fetch_page", side_effect=_fake_fetch_pages(CANNED_PAGES)), \
             patch.object(web_discovery, "extract_grant_programs", side_effect=_fake_extract):
            call_command("discover_grant_pages", "--project-id", str(project.pk), "--dry-run")
        out = capsys.readouterr().out
        assert "Program on grants" in out
        assert GRANTS_URL in out
        assert "Dry run" in out
        assert Opportunity.objects.count() == 0

    def test_llm_missing_reports_gracefully(self, project, funder, capsys):
        with patch("openoutreach.core.llm.get_llm_model",
                   side_effect=ValueError("LLM_API_KEY is not set")):
            call_command("discover_grant_pages", "--project-id", str(project.pk))
        out = capsys.readouterr().out
        assert "LLM not configured" in out
        assert Opportunity.objects.count() == 0

    def test_unknown_project_errors(self, db):
        from django.core.management.base import CommandError
        with pytest.raises(CommandError):
            call_command("discover_grant_pages", "--project-id", "999999")


def test_reserved_domain_catches_bare_urls():
    # Regression: "https://example.org" (no www) used to slip the reserved-domain
    # gate because the regex required ^ or "." before the domain.
    from openoutreach.funding.grounding import is_reserved_domain
    assert is_reserved_domain("https://example.org")
    assert is_reserved_domain("http://example.com/grants")
    assert is_reserved_domain("example.org")
    assert not is_reserved_domain("https://myexample.org")
    assert not is_reserved_domain("https://real-example-fund.org")
    assert not is_reserved_domain("")
