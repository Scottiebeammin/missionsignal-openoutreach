import pytest
from django.core import mail
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse

from openoutreach.funding.models import Opportunity
from openoutreach.signals.demo import seed_missionsignal_demo
from openoutreach.signals.models import InterestSignup, OrganizationSourcePage, PilotProfile


pytestmark = pytest.mark.django_db


@pytest.fixture
def snapshot_project(db):
    user, _organization, project = seed_missionsignal_demo()
    # The product now scopes opportunities to a project (live ingest stamps
    # Opportunity.project); the demo seed writes a global catalog, so adopt it
    # into the demo project the way live ingest would.
    Opportunity.objects.filter(project__isnull=True).update(project=project)
    return project, user


def test_public_landing_page_renders_without_login(client):
    response = client.get(reverse("anansi-atlas-landing"))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Anansi Atlas" in content
    assert "The Web of Opportunity" in content
    assert "Your mission deserves a map." in content
    assert "Not a mountain of research." in content
    assert "Opportunity Web Snapshot" in content
    assert "Apply Now" in content
    assert "$150/mo" in content
    assert "$150/month" in content
    assert "locked for life" in content
    assert "sign up today" in content.lower()
    assert "Limited-time offer" in content
    # The founding-cohort framing is retired: no seat caps or cohort copy.
    assert "founding cohort" not in content.lower()
    assert "founding seat" not in content.lower()
    assert "20 seats" not in content.lower()
    assert "Scott Foundry Group LLC" in content
    assert "anansiatlas.com" in content
    # Pricing copy rule: the Snapshot is never marketed as free.
    assert "free snapshot" not in content.lower()


def test_public_landing_page_shows_annual_offer_when_configured(client, monkeypatch):
    annual_url = "https://buy.stripe.com/test-annual"
    monkeypatch.setenv("STRIPE_ANNUAL_URL", annual_url)

    response = client.get(reverse("anansi-atlas-landing"))
    content = response.content.decode()

    assert response.status_code == 200
    assert annual_url in content
    assert "$1,440/year" in content
    assert "save 20%" in content


def test_public_landing_page_renders_waitlist_form_fields(client):
    response = client.get(reverse("anansi-atlas-landing"))
    content = response.content.decode()

    assert response.status_code == 200
    assert 'method="post"' in content
    assert 'name="name"' in content
    assert 'name="organization"' in content
    assert 'name="email"' in content
    assert 'name="role"' in content
    assert 'name="interest_type" value="founding_atlas_partners"' in content
    assert 'name="message"' in content  # ask-a-question form
    assert "Apply Now" in content


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_interest_signup_form_submission_stores_local_record_and_sends_emails(client):
    mail.outbox = []
    response = client.post(
        reverse("anansi-atlas-landing"),
        {
            "name": "Jordan Lee",
            "organization": "Mission Works",
            "email": "jordan@example.org",
            "role": "Executive Director",
            "website": "https://mission.example.org",
            "interest_type": InterestSignup.InterestType.FOUNDING_ATLAS_PARTNERS,
            "message": "We want a snapshot.",
        },
    )

    signup = InterestSignup.objects.get()
    assert response.status_code == 302
    assert response.url == reverse("anansi-atlas-thanks")
    assert signup.name == "Jordan Lee"
    assert signup.organization == "Mission Works"
    assert signup.email == "jordan@example.org"
    assert signup.status == InterestSignup.Status.NEW
    pilot = PilotProfile.objects.get(signup=signup)
    assert pilot.organization_name == "Mission Works"
    assert pilot.contact_name == "Jordan Lee"
    assert pilot.email == "jordan@example.org"
    assert pilot.lifecycle_status == PilotProfile.LifecycleStatus.WAITLIST
    # Operator notification only — submitter confirmations are OFF by default
    # after the Aug 2026 bounce storm (bots feeding junk addresses to the form).
    assert len(mail.outbox) == 1
    (notification,) = mail.outbox
    assert notification.to == ["info@anansiatlas.com", "marcus@anansiatlas.com"]
    assert notification.subject == "New Anansi Atlas interest signup"
    assert "Name: Jordan Lee" in notification.body
    assert "Organization: Mission Works" in notification.body
    assert "Email: jordan@example.org" in notification.body
    assert "Role / Title: Executive Director" in notification.body
    assert "Website: https://mission.example.org" in notification.body
    assert "Interest Type: Join Founding Atlas Partners" in notification.body
    assert "Message: We want a snapshot." in notification.body
    assert "Created At:" in notification.body


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_interest_signup_confirmation_sends_only_when_flag_enabled(client, monkeypatch):
    monkeypatch.setenv("ATLAS_FORM_CONFIRMATIONS_ENABLED", "true")
    mail.outbox = []
    client.post(
        reverse("anansi-atlas-landing"),
        {
            "name": "Jordan Lee",
            "organization": "Mission Works",
            "email": "jordan@example.org",
            "role": "Executive Director",
            "website": "https://mission.example.org",
            "interest_type": InterestSignup.InterestType.FOUNDING_ATLAS_PARTNERS,
            "message": "We want a snapshot.",
        },
    )
    assert len(mail.outbox) == 2
    confirmation = mail.outbox[1]
    assert confirmation.to == ["jordan@example.org"]
    assert confirmation.subject == "You're on the Anansi Atlas waitlist"
    assert "Hi Jordan," in confirmation.body


def test_interest_signup_email_failure_does_not_break_signup(client, monkeypatch):
    def fail_send_mail(*args, **kwargs):
        raise RuntimeError("email server unavailable")

    monkeypatch.setattr("openoutreach.signals.notifications.send_mail", fail_send_mail)

    response = client.post(
        reverse("anansi-atlas-landing"),
        {
            "name": "Taylor Kim",
            "organization": "Neighborhood Futures",
            "email": "taylor@example.org",
            "role": "Development Director",
            "website": "https://neighborhood.example.org",
            "interest_type": InterestSignup.InterestType.FOUNDING_ATLAS_PARTNERS,
            "message": "We want to join the pilot.",
        },
    )

    signup = InterestSignup.objects.get()
    assert response.status_code == 302
    assert response.url == reverse("anansi-atlas-thanks")
    assert signup.name == "Taylor Kim"
    assert signup.organization == "Neighborhood Futures"
    assert signup.email == "taylor@example.org"
    assert signup.status == InterestSignup.Status.NEW
    assert PilotProfile.objects.filter(signup=signup).exists()


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_interest_signup_invalid_submission_shows_errors_and_does_not_save(client):
    mail.outbox = []

    response = client.post(
        reverse("anansi-atlas-landing"),
        {
            "name": "",
            "organization": "Mission Works",
            "email": "not-an-email",
            "interest_type": InterestSignup.InterestType.OPPORTUNITY_WEB_SNAPSHOT,
        },
    )
    content = response.content.decode()

    assert response.status_code == 200
    assert InterestSignup.objects.count() == 0
    assert len(mail.outbox) == 0
    assert "This field is required." in content
    assert "Enter a valid email address." in content


def test_interest_signup_confirmation_page(client):
    response = client.get(reverse("anansi-atlas-thanks"))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Thank you" in content
    assert "Opportunity Web Snapshot" in content
    assert "limited-time $150/month offer" in content


def test_pilot_onboarding_route_renders_without_login(client):
    response = client.get(reverse("pilot-onboarding"))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Limited-Time Offer" in content
    assert "Become an Atlas Partner." in content
    assert "Limited-time offer" in content
    assert "Request pilot access" in content
    # What's included
    assert "Opportunity Web Snapshot" in content
    assert "Executive Dashboard Access" in content
    assert "Opportunity Web Access" in content
    assert "Readiness &amp; Relationship Review" in content
    assert "Founder-Led Walkthrough" in content
    assert "30-Day Action Plan" in content
    assert "30 Days Platform Access" in content
    assert "Early Partner Recognition" in content
    # How it works
    assert "Submit interest" in content
    assert "Organization intake" in content
    assert "Snapshot + walkthrough" in content
    assert "30-day action period" in content
    # Founder strip
    assert "Marcus Scott" in content
    assert "Founder, Anansi Atlas" in content
    assert "Scott Foundry Group LLC" in content
    # FAQ
    assert "What is Anansi Atlas?" in content
    assert "What is an Opportunity Web Snapshot?" in content
    assert "How long does the pilot last?" in content


def test_project_member_can_view_opportunity_web_snapshot(client, snapshot_project):
    project, user = snapshot_project
    OrganizationSourcePage.objects.create(
        organization=project.organization,
        project=project,
        title="Founder research notes",
        source_type=OrganizationSourcePage.SourceType.FOUNDER_NOTES,
        notes="Website observations and local funder research for Snapshot production.",
        raw_text="Bright Future has strong workforce alignment and needs partner evidence.",
        relevance=OrganizationSourcePage.Relevance.HIGH,
        review_status=OrganizationSourcePage.ReviewStatus.USED_IN_SNAPSHOT,
    )
    client.force_login(user)

    response = client.get(reverse("project-snapshot", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Opportunity Web Snapshot" in content
    assert "Readiness Score" in content
    assert "Executive Summary" in content
    assert "30-Day Action Plan" in content
    assert "Top Funder Pathways" in content
    assert "Named Funder Targets" in content
    assert "Partner Pathways" in content
    assert "Ecosystem Gaps to Close" in content
    assert "Top Opportunities" in content
    assert "Relationship Intelligence" in content
    assert "Top Relationships To Build" in content
    assert "Opportunity Pathways" in content
    assert "Network Health" in content
    assert "Readiness Context" in content
    assert "Risks and Gaps" in content
    assert "Top Risks" in content
    assert "Top Resource Gaps" in content
    assert "Organization Intelligence" in content
    assert "Source Summary" in content
    assert "Sources reviewed" in content
    assert "Funders reviewed" in content
    assert "Opportunities reviewed" in content
    # Deterministic demo intelligence (Orlando-themed seed data)
    assert "Central Florida Corporate Giving Program" in content
    assert "United Way of Greater Orlando" in content
    assert "Orlando Community College Career Pathways" in content
    assert "City of Orlando Youth and Workforce Office" in content
    assert "Youth Opportunity Grant" in content
    # Rationale / transparency labels
    assert "Why this appears" in content
    assert "Why now" in content
    assert "Preparation required" in content
    assert "Unlocks:" in content
    assert "High Impact" in content
    assert "Mission Alignment" in content
    assert "Strong Geographic Fit" in content
    assert "Excellent Fit" in content
    assert "Verified Opportunity" in content
    assert "Reviewed Source" in content
    assert "Source reference:" in content
    assert "This aligns with the organizational priority:" in content
    assert "Book your Founder Walkthrough" in content


def test_non_member_cannot_view_opportunity_web_snapshot(client, snapshot_project):
    project, _user = snapshot_project
    outsider = get_user_model().objects.create_user(username="snapshot-outsider")
    client.force_login(outsider)

    response = client.get(reverse("project-snapshot", kwargs={"pk": project.pk}))

    assert response.status_code == 404


def test_dashboard_and_web_link_to_snapshot(client, snapshot_project):
    project, user = snapshot_project
    client.force_login(user)

    dashboard = client.get(reverse("project-dashboard", kwargs={"pk": project.pk})).content.decode()
    web = client.get(reverse("project-opportunity-web", kwargs={"pk": project.pk})).content.decode()
    snapshot_url = reverse("project-snapshot", kwargs={"pk": project.pk})

    assert "Open Snapshot" in dashboard
    assert snapshot_url in dashboard
    assert "View Full Snapshot" in web
    assert snapshot_url in web
