import pytest
from django.core import mail
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse

from openoutreach.signals.demo import seed_missionsignal_demo
from openoutreach.signals.models import InterestSignup


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
    assert "Marcus Scott" in content
    assert "anansiatlas.com" in content
    assert "Scott Foundry Group LLC" in content


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
    assert "Shape a smarter way to see opportunity" in content
    assert "Mission and programs" in content
    assert "Geography" in content
    assert "Funders and partners" in content
    assert "Resources and evidence" in content


def test_project_member_can_view_opportunity_web_snapshot(client, snapshot_project):
    project, user = snapshot_project
    client.force_login(user)

    response = client.get(reverse("project-snapshot", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Opportunity Web Snapshot V1" in content
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
