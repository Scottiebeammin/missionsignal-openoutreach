import pytest
from django.contrib.auth import get_user_model
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
    assert "Map the web of opportunity around your mission." in content
    assert "Get Your Opportunity Web Snapshot" in content
    assert "Join the Founding Atlas Partners" in content
    assert "anansiatlas.com" in content
    assert "Scott Foundry Group LLC" in content


def test_interest_signup_form_submission_stores_local_record(client):
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
    assert "Mission" in content
    assert "Programs" in content
    assert "Geography" in content
    assert "Beneficiaries" in content
    assert "Documents and evidence" in content


def test_project_member_can_view_opportunity_web_snapshot(client, snapshot_project):
    project, user = snapshot_project
    client.force_login(user)

    response = client.get(reverse("project-snapshot", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Opportunity Web Snapshot V1" in content
    assert "Mission Overview" in content
    assert "Opportunity Web Summary" in content
    assert "Readiness Score" in content
    assert "Top Funder Pathways" in content
    assert "Top Partner Pathways" in content
    assert "Top Resource Gaps" in content
    assert "Top Opportunities" in content
    assert "Top Risks / Gaps" in content
    assert "Top 5 Recommended Next Actions" in content


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
