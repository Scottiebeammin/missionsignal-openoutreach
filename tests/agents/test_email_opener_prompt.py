# tests/agents/test_email_opener_prompt.py
"""The email opener shares _outreach_base.j2 with the follow-up agent — verify
the company-intel injection reaches the cold-email prompt too."""
from tests.factories import DealFactory, LeadFactory


def test_opener_prompt_includes_company_intel(db, fake_session):
    from openoutreach.core.agents.prompt import base_context, render

    lead = LeadFactory(public_identifier="dave", company_intel={
        "domain": "acme.com",
        "company_name": "Acme Robotics",
        "industry_signals": ["Fintech"],
    })
    deal = DealFactory(lead=lead, campaign=fake_session.campaign)
    fake_session.self_profile = {"first_name": "Bob", "last_name": "Builder", "urn": "urn:li:fsd_profile:SELF"}

    prompt = render("email_opener.j2", **base_context(fake_session, deal))

    assert "cold outreach email" in prompt          # opener framing intact
    assert "Their Company (from their website)" in prompt
    assert "Acme Robotics (acme.com)" in prompt


def test_opener_prompt_without_intel_has_no_company_section(db, fake_session):
    from openoutreach.core.agents.prompt import base_context, render

    lead = LeadFactory(public_identifier="erin")
    deal = DealFactory(lead=lead, campaign=fake_session.campaign)
    fake_session.self_profile = {"first_name": "Bob", "last_name": "Builder", "urn": "urn:li:fsd_profile:SELF"}

    prompt = render("email_opener.j2", **base_context(fake_session, deal))

    assert "Their Company" not in prompt
