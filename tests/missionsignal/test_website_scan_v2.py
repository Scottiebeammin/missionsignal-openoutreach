"""Website scan v2: multi-page scraping + monthly drift-nudge command.

- scrape_site_text pulls the homepage plus same-host about/program pages, so a
  program listed on /programs (not the homepage) is found.
- rescan_websites re-verifies every project and emails the owner ONLY when a
  new claim has gone missing since the last check (drift), not on steady-state
  mismatches the client already knows about.
"""
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command

from openoutreach.core.models import Organization, OrganizationMember, Project

pytestmark = pytest.mark.django_db


# ── multi-page scraper ──────────────────────────────────────────────────────

def test_scrape_site_text_follows_program_subpage():
    from openoutreach.signals import website_scraper

    home_html = (
        '<html><body><h1>Bright Paths</h1>'
        '<a href="/programs/">Our Programs</a>'
        '<a href="https://other.com/x">External</a>'
        '</body></html>'
    )
    programs_html = '<html><body>Career Mentorship Circle for local youth.</body></html>'

    class FakeResp:
        def __init__(self, text): self.text = text
        def raise_for_status(self): pass

    requested = []

    class FakeClient:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def get(self, url):
            requested.append(url)
            return FakeResp(programs_html if "programs" in url else home_html)

    with patch.object(website_scraper.httpx, "Client", FakeClient):
        text = website_scraper.scrape_site_text("https://brightpaths.org", max_pages=3)
    assert "Bright Paths" in text              # homepage
    assert "Career Mentorship Circle" in text  # followed subpage
    # Only same-host pages were fetched; the external link was never requested.
    assert any("programs" in u for u in requested)
    assert not any("other.com" in u for u in requested)


# ── drift nudge command ─────────────────────────────────────────────────────

@pytest.fixture
def project_with_owner(db):
    org = Organization.objects.create(name="Bright Paths", mission="Serve youth.",
                                      website="https://brightpaths.org")
    project = Project.objects.create(name="Bright Paths", organization=org)
    project.program_summaries = [
        {"name": "Digital Skills Lab", "description": "x"},
        {"name": "Career Mentorship Circle", "description": "x"},
    ]
    project.save(update_fields=["program_summaries"])
    org.focus_areas = ["Youth Development"]
    org.save(update_fields=["focus_areas"])
    user = get_user_model().objects.create_user(username="ed@bp.org", email="ed@bp.org", password="x")
    project.users.add(user)
    OrganizationMember.objects.create(user=user, project=project, is_admin=True, contact_name="ED")
    return project, user


def test_rescan_emails_owner_on_new_drift(project_with_owner):
    project, user = project_with_owner
    # Site mentions the lab but NOT the mentorship circle → drift on that claim.
    site = "Digital Skills Lab supports youth development in Orlando."
    with patch("openoutreach.signals.website_verification.scrape_site_text", return_value=site):
        call_command("rescan_websites")
    assert len(mail.outbox) == 1
    body = mail.outbox[0].body
    assert "Career Mentorship Circle" in body
    assert "Digital Skills Lab" not in body  # found item is not nagged


def test_rescan_no_email_when_drift_unchanged(project_with_owner):
    project, user = project_with_owner
    site = "Digital Skills Lab supports youth development in Orlando."
    with patch("openoutreach.signals.website_verification.scrape_site_text", return_value=site):
        call_command("rescan_websites")           # first run: nudges once
        mail.outbox.clear()
        call_command("rescan_websites")           # same drift → no new nudge
    assert len(mail.outbox) == 0


def test_rescan_no_email_flag(project_with_owner):
    project, user = project_with_owner
    site = "Only the homepage tagline."
    with patch("openoutreach.signals.website_verification.scrape_site_text", return_value=site):
        call_command("rescan_websites", "--no-email")
    assert len(mail.outbox) == 0
    project.organization.refresh_from_db()
    assert project.organization.website_check["status"] == "ok"  # still rescanned
