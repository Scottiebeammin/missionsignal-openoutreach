# tests/emails/test_company_intel.py
"""Company-intel enrichment — parse fixture HTML (no network) + tri-state resolve.

The analyzer is mocked at its ``_fetch`` boundary so no test hits the network.
``Lead.resolve_company_intel`` mirrors ``resolve_api_email``'s tri-state:
True (data), False (ran, empty), None (couldn't run).
"""
from unittest.mock import patch

import pytest

from openoutreach.emails import company_intel
from openoutreach.emails.company_intel import analyze_company, domain_from_email, intel_digest

_HOME_HTML = """
<html><head>
<title>Acme Robotics — Industrial AI</title>
<meta property="og:site_name" content="Acme Robotics">
<meta name="description" content="AI-powered machine learning for manufacturing.">
<meta name="generator" content="Next.js">
<script src="https://js.stripe.com/v3/"></script>
<script type="application/ld+json">
{"@type": "Person", "name": "Jane Doe", "jobTitle": "CEO", "url": "https://acme.com/jane"}
</script>
</head><body>
<h1>Acme Robotics</h1>
<p>We are hiring! View all jobs.</p>
<p>Series B funded. 250+ employees.</p>
<a href="https://www.linkedin.com/company/acme-robotics">LinkedIn</a>
<a href="https://github.com/acme">GitHub</a>
<a href="mailto:hello@acme.com">Contact</a>
</body></html>
"""


# ── domain_from_email ─────────────────────────────────────────────────

class TestDomainFromEmail:
    def test_work_email_returns_domain(self):
        assert domain_from_email("jane@acme.com") == "acme.com"

    def test_uppercase_and_trailing_dot_normalized(self):
        assert domain_from_email("Jane@Acme.COM.") == "acme.com"

    @pytest.mark.parametrize("email", [
        "jane@gmail.com", "jane@outlook.com", "jane@proton.me", "jane@yahoo.com",
    ])
    def test_free_mail_is_none(self, email):
        assert domain_from_email(email) is None

    @pytest.mark.parametrize("email", ["", None, "notanemail", "jane@localhost"])
    def test_garbage_is_none(self, email):
        assert domain_from_email(email) is None


# ── analyze_company ───────────────────────────────────────────────────

class TestAnalyzeCompany:
    def test_extracts_firmographics_from_homepage(self):
        # Homepage returns HTML; every subpage 404s.
        def fake_fetch(url, timeout=8):
            if url in ("https://acme.com", "https://acme.com/"):
                return 200, _HOME_HTML
            return 404, None

        with patch.object(company_intel, "_fetch", side_effect=fake_fetch):
            result = analyze_company("acme.com")

        assert result["company_name"] == "Acme Robotics"
        assert "AI/ML" in result["industry_signals"]
        assert "Stripe" in result["tech_stack"]
        assert "Next.js" in result["tech_stack"]
        assert result["social_links"]["linkedin"] == ["https://www.linkedin.com/company/acme-robotics"]
        assert result["has_job_postings"] is True
        assert result["company_size_signals"]["estimated_employees"] == "250"
        assert result["company_size_signals"]["funding_stage"] == "Series B"
        assert {"name": "Jane Doe", "title": "CEO", "url": "https://acme.com/jane"} in result["team_members"]
        assert "hello@acme.com" in result["contact_info"]["emails"]

    def test_bare_domain_gets_https_scheme(self):
        seen = []

        def fake_fetch(url, timeout=8):
            seen.append(url)
            return (200, _HOME_HTML) if not seen[:-1] else (404, None)

        with patch.object(company_intel, "_fetch", side_effect=fake_fetch):
            analyze_company("acme.com")
        assert seen[0] == "https://acme.com"

    def test_homepage_unfetchable_returns_none(self):
        with patch.object(company_intel, "_fetch", return_value=(None, None)):
            assert analyze_company("acme.com") is None


# ── Lead.resolve_company_intel (tri-state) ────────────────────────────

class TestResolveCompanyIntel:
    def _lead(self, **kwargs):
        from openoutreach.crm.models import Lead
        defaults = dict(public_identifier="alice",
                        linkedin_url="https://www.linkedin.com/in/alice/")
        defaults.update(kwargs)
        return Lead.objects.create(**defaults)

    def test_disabled_flag_is_none(self, db):
        lead = self._lead(api_email="jane@acme.com")
        with patch("openoutreach.core.conf.COMPANY_INTEL_ENABLED", False):
            assert lead.resolve_company_intel() is None
        lead.refresh_from_db()
        assert lead.company_intel is None

    def test_no_email_is_none(self, db):
        lead = self._lead(api_email=None)
        assert lead.resolve_company_intel() is None
        lead.refresh_from_db()
        assert lead.company_intel is None

    def test_free_mail_email_is_none(self, db):
        lead = self._lead(api_email="jane@gmail.com")
        assert lead.resolve_company_intel() is None

    def test_hit_persists_intel_and_returns_true(self, db):
        lead = self._lead(api_email="jane@acme.com")
        intel = {"domain": "acme.com", "industry_signals": ["AI/ML"]}
        with patch("openoutreach.emails.company_intel.analyze_company", return_value=intel) as mock:
            assert lead.resolve_company_intel() is True
        mock.assert_called_once_with("acme.com")
        lead.refresh_from_db()
        assert lead.company_intel == intel

    def test_empty_result_stamps_tried_and_returns_false(self, db):
        lead = self._lead(api_email="jane@acme.com")
        with patch("openoutreach.emails.company_intel.analyze_company", return_value=None):
            assert lead.resolve_company_intel() is False
        lead.refresh_from_db()
        assert lead.company_intel == {}

    def test_idempotent_on_non_null(self, db):
        lead = self._lead(api_email="jane@acme.com", company_intel={"cached": True})
        with patch("openoutreach.emails.company_intel.analyze_company") as mock:
            assert lead.resolve_company_intel() is True
        mock.assert_not_called()

    # — connect-leg fallback: domain from the CONNECTED contact-info overlay —

    def test_overlay_email_fallback_when_no_api_email(self, db):
        lead = self._lead(api_email=None, contact_info={"email": "jane@acme.com"})
        intel = {"domain": "acme.com"}
        with patch("openoutreach.emails.company_intel.analyze_company", return_value=intel) as mock:
            assert lead.resolve_company_intel() is True
        mock.assert_called_once_with("acme.com")
        lead.refresh_from_db()
        assert lead.company_intel == intel

    def test_overlay_emails_list_skips_free_mail(self, db):
        lead = self._lead(api_email=None, contact_info={
            "email": None, "emails": ["jane@gmail.com", "jane@acme.com"],
        })
        with patch("openoutreach.emails.company_intel.analyze_company", return_value={"domain": "acme.com"}) as mock:
            assert lead.resolve_company_intel() is True
        mock.assert_called_once_with("acme.com")

    def test_api_email_takes_precedence_over_overlay(self, db):
        lead = self._lead(api_email="jane@corp.io", contact_info={"email": "jane@other.com"})
        with patch("openoutreach.emails.company_intel.analyze_company", return_value={"domain": "corp.io"}) as mock:
            lead.resolve_company_intel()
        mock.assert_called_once_with("corp.io")

    def test_personal_only_overlay_is_none(self, db):
        lead = self._lead(api_email=None, contact_info={
            "email": "jane@gmail.com", "emails": ["jane@yahoo.com"], "phone_numbers": [],
        })
        assert lead.resolve_company_intel() is None
        lead.refresh_from_db()
        assert lead.company_intel is None  # nothing stamped — a later source can retry


# ── intel_digest (prompt injection formatter) ─────────────────────────

class TestIntelDigest:
    def test_full_intel_renders_all_lines(self):
        digest = intel_digest({
            "domain": "acme.com",
            "company_name": "Acme Robotics",
            "description": "Industrial AI.",
            "industry_signals": ["AI/ML", "DevTools"],
            "tech_stack": ["Next.js", "Stripe"],
            "company_size_signals": {"estimated_employees": "250", "funding_stage": "Series B"},
            "has_job_postings": True,
        })
        assert "- Company: Acme Robotics (acme.com)" in digest
        assert "- What they do: Industrial AI." in digest
        assert "- Industry: AI/ML, DevTools" in digest
        assert "- Size/funding: ~250 employees, Series B" in digest
        assert "- Actively hiring" in digest
        assert "- Website tech: Next.js, Stripe" in digest

    @pytest.mark.parametrize("intel", [None, {}])
    def test_no_intel_is_empty_string(self, intel):
        assert intel_digest(intel) == ""

    def test_partial_intel_renders_only_present_lines(self):
        digest = intel_digest({"domain": "acme.com", "industry_signals": ["Fintech"]})
        assert digest == "- Company: acme.com\n- Industry: Fintech"
