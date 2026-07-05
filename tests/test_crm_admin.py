# tests/test_crm_admin.py
"""Smoke tests for the Lead admin — changelist, intel filter, detail panel."""
import pytest

from openoutreach.crm.models import Lead

INTEL = {
    "domain": "acme.com",
    "company_name": "Acme Robotics",
    "description": "Industrial AI.",
    "industry_signals": ["AI/ML", "DevTools"],
    "tech_stack": ["Next.js", "Stripe"],
    "social_links": {"linkedin": ["https://www.linkedin.com/company/acme"]},
    "company_size_signals": {"estimated_employees": "250", "funding_stage": "Series B"},
    "has_job_postings": True,
    "team_members": [{"name": "Jane Doe", "title": "CEO", "url": ""}],
    "contact_info": {"emails": ["hello@acme.com"], "phones": []},
    "pages_analyzed": ["https://acme.com"],
}


def _lead(public_id, **kwargs):
    return Lead.objects.create(
        public_identifier=public_id,
        linkedin_url=f"https://www.linkedin.com/in/{public_id}/",
        **kwargs,
    )


@pytest.mark.django_db
class TestLeadAdmin:
    def test_changelist_renders(self, admin_client):
        _lead("alice", company_intel=INTEL)
        _lead("bob")
        resp = admin_client.get("/admin/crm/lead/")
        assert resp.status_code == 200
        assert b"Acme Robotics" in resp.content

    @pytest.mark.parametrize("value,expected,absent", [
        ("yes", b"alice", b"bob"),
        ("no", b"bob", b"alice"),
    ])
    def test_intel_filter(self, admin_client, value, expected, absent):
        _lead("alice", company_intel=INTEL)
        _lead("bob")
        resp = admin_client.get(f"/admin/crm/lead/?intel={value}")
        assert resp.status_code == 200
        assert expected in resp.content
        assert absent not in resp.content

    def test_intel_filter_tried_empty(self, admin_client):
        _lead("alice", company_intel=INTEL)
        _lead("carol", company_intel={})
        resp = admin_client.get("/admin/crm/lead/?intel=empty")
        assert resp.status_code == 200
        assert b"carol" in resp.content
        assert b"alice" not in resp.content

    def test_detail_renders_intel_panel(self, admin_client):
        lead = _lead("alice", company_intel=INTEL)
        resp = admin_client.get(f"/admin/crm/lead/{lead.pk}/change/")
        assert resp.status_code == 200
        for fragment in (b"Acme Robotics", b"AI/ML", b"Series B", b"Jane Doe"):
            assert fragment in resp.content

    def test_detail_renders_when_intel_null(self, admin_client):
        lead = _lead("bob")
        resp = admin_client.get(f"/admin/crm/lead/{lead.pk}/change/")
        assert resp.status_code == 200
        assert b"Not resolved yet" in resp.content

    def test_intel_values_are_escaped(self, admin_client):
        """Scraped values are attacker-controlled — must be HTML-escaped."""
        evil = dict(INTEL, company_name="<script>alert(1)</script>")
        lead = _lead("mallory", company_intel=evil)
        resp = admin_client.get(f"/admin/crm/lead/{lead.pk}/change/")
        assert resp.status_code == 200
        assert b"<script>alert(1)</script>" not in resp.content
