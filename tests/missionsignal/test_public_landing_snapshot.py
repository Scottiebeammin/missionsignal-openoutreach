import pytest
from django.core import mail
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse

from openoutreach.signals.demo import seed_missionsignal_demo
from openoutreach.signals.models import InterestSignup, OrganizationSourcePage, PilotProfile


pytestmark = pytest.mark.django_db


@pytest.fixture
def snapshot_project(db):
    user, _organization, project = seed_missionsignal_demo()
    return project, user


def test_public_landing_page_renders_without_login(client):
    response = client.get(reverse("anansi-atlas-landing"))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Anansi Atlas" in content
    assert "The Web of Opportunity" in content
    assert "Map the Web of Opportunity Around Your Mission" in content
    assert "funders, potential partners, community resources, strategic risks, pathways" in content
    assert "Explore the Opportunity Web Snapshot" in content
    assert "Become a Founding Atlas Partner" in content
    assert "$100 pilot package" in content
    assert "Limited to the first 10 partners" in content
    assert "30-day action plan" in content
    assert "Marcus Scott" in content
    assert "anansiatlas.com" in content
    assert "Scott Foundry Group LLC" in content


def test_public_landing_page_renders_waitlist_form_fields(client):
    response = client.get(reverse("anansi-atlas-landing"))
    content = response.content.decode()

    assert response.status_code == 200
    assert '<form method="post">' in content
    assert 'name="name"' in content
    assert 'name="organization"' in content
    assert 'name="email"' in content
    assert 'name="role"' in content
    assert 'name="website"' in content
    assert 'name="interest_type"' in content
    assert 'name="message"' in content
    assert "Explore the Opportunity Web Snapshot" in content


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_interest_signup_form_submission_stores_local_record_and_sends_email(client):
    mail.outbox = []
    response = client.post(
        reverse("anansi-atlas-landing"),
        {
            "name": "Jordan Lee",
            "organization": "Mission Works",
            "email": "jordan@example.org",
            "role": "Executive Director",
            "website": "https://mission.example.org",
            "interest_type": InterestSignup.InterestType.OPPORTUNITY_WEB_SNAPSHOT,
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
    assert len(mail.outbox) == 1
    notification = mail.outbox[0]
    assert notification.to == ["info@anansiatlas.com"]
    assert notification.subject == "New Anansi Atlas interest signup"
    assert "Name: Jordan Lee" in notification.body
    assert "Organization: Mission Works" in notification.body
    assert "Email: jordan@example.org" in notification.body
    assert "Role / Title: Executive Director" in notification.body
    assert "Website: https://mission.example.org" in notification.body
    assert "Interest Type: Get Opportunity Web Snapshot" in notification.body
    assert "Message: We want a snapshot." in notification.body
    assert "Created At:" in notification.body


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
    assert "Founding Atlas Partners" in content


def test_pilot_onboarding_route_renders_without_login(client):
    response = client.get(reverse("pilot-onboarding"))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Founding Atlas Partners" in content
    assert "Become a Founding Atlas Partner" in content
    assert "$100" in content
    assert "Limited to the first 10 Founding Atlas Partners" in content
    assert "Opportunity Web Snapshot" in content
    assert "30 Days Platform Access" in content
    assert "Executive Dashboard Access" in content
    assert "Readiness Review" in content
    assert "Relationship Review" in content
    assert "Founder-Led Walkthrough" in content
    assert "30-Day Action Plan" in content
    assert "Founding Atlas Partner Recognition" in content
    assert "Pilot onboarding flow" in content
    assert "Submit interest" in content
    assert "Welcome and scheduling" in content
    assert "Organization intake" in content
    assert "Opportunity Web Snapshot generation" in content
    assert "Founder walkthrough" in content
    assert "30-day action period" in content
    assert "Feedback and refinement" in content
    assert "Snapshot deliverable" in content
    assert "Executive Summary" in content
    assert "Top Opportunities" in content
    assert "Relationship Gaps" in content
    assert "Readiness Gaps" in content
    assert "Strategic Moves" in content
    assert "30-Day Recommendations" in content
    assert "Marcus Scott, Founder, Anansi Atlas" in content
    assert "Pilot FAQ" in content
    assert "What is Anansi Atlas?" in content
    assert "What is an Opportunity Web Snapshot?" in content
    assert "How long does the pilot last?" in content
    assert "Mission and programs" in content
    assert "Geography" in content
    assert "Funders and partners" in content
    assert "Resources and evidence" in content


def test_project_member_can_view_opportunity_web_snapshot(client, snapshot_project):
    project, user = snapshot_project
    OrganizationSourcePage.objects.create(
        organization=project.organization,
        project=project,
        title="Founder research notes",
        source_type=OrganizationSourcePage.SourceType.FOUNDER_NOTES,
        notes="Website observations and local funder research for Snapshot production.",
        raw_text="BridgeForward has strong workforce alignment and needs partner evidence.",
        relevance=OrganizationSourcePage.Relevance.HIGH,
        review_status=OrganizationSourcePage.ReviewStatus.USED_IN_SNAPSHOT,
    )
    client.force_login(user)

    response = client.get(reverse("project-snapshot", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Opportunity Web Snapshot · Consulting Deliverable" in content
    assert "30-Day Action Plan" in content
    assert "What This Delivers" in content
    assert "Executive Summary" in content
    assert "Opportunity Overview" in content
    assert "Readiness Score" in content
    assert "Top Funder Pathways" in content
    assert "Top Partner Pathways" in content
    assert "Top Resource Gaps" in content
    assert "Top Opportunities" in content
    assert "Top Risks" in content
    assert "Top Relationship Gaps" in content
    assert "Top Recommended Actions" in content
    assert "Why this appears" in content
    assert "Mission Alignment" in content
    assert "Geographic Alignment" in content
    assert "Skills Training Funders" in content
    assert "Named Relationship Targets" in content
    assert "Pursue County Workforce Board" in content
    assert "Source Summary" in content
    assert "Sources reviewed" in content
    assert "Founder research notes" in content
    assert "Missing Source Guidance" in content
    assert "Add program descriptions to improve opportunity matching." in content


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

    assert "View Opportunity Web Snapshot" in dashboard
    assert snapshot_url in dashboard
    assert "View Opportunity Web Snapshot" in web
    assert snapshot_url in web
