import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.urls import reverse

from openoutreach.signals.demo import seed_missionsignal_demo
from openoutreach.signals.models import PilotFeedback, PilotProfile
from openoutreach.signals.pilot import build_pilot_context


pytestmark = pytest.mark.django_db


@pytest.fixture
def pilot_project(db):
    user, _organization, project = seed_missionsignal_demo()
    return project, user


def test_pilot_models_have_expected_defaults_and_admin_registration(pilot_project):
    project, _user = pilot_project
    profile = PilotProfile.objects.create(
        project=project,
        organization_name="BridgeForward Digital Futures",
        contact_name="Jordan Lee",
        email="jordan@example.org",
    )

    assert str(profile) == "BridgeForward Digital Futures pilot"
    assert profile.lifecycle_status == PilotProfile.LifecycleStatus.WAITLIST
    assert profile.snapshot_status == PilotProfile.SnapshotStatus.REVIEWING_ORGANIZATION
    assert profile.walkthrough_status == PilotProfile.WalkthroughStatus.NOT_SCHEDULED
    assert PilotProfile in admin.site._registry
    assert PilotFeedback in admin.site._registry


def test_pilot_context_renders_checklist_progress_and_snapshot_state(pilot_project):
    project, _user = pilot_project
    profile = PilotProfile.objects.create(
        project=project,
        organization_name="BridgeForward Digital Futures",
        website="https://bridgeforward.example.org",
        mission="Expand digital access.",
        primary_programs="Youth technology training.",
        communities_served="Cleveland youth",
        top_goals="Secure pilot partners.",
        snapshot_status=PilotProfile.SnapshotStatus.DELIVERED,
        lifecycle_status=PilotProfile.LifecycleStatus.SNAPSHOT_DELIVERED,
    )

    context = build_pilot_context(profile)

    assert context.current_stage == "Snapshot Delivered"
    assert context.snapshot_ready is True
    assert context.progress_percentage >= 75
    assert "Complete Discovery Questionnaire" in [item.label for item in context.checklist]


def test_project_member_can_view_pilot_workspace(client, pilot_project):
    project, user = pilot_project
    PilotProfile.objects.create(project=project, organization_name="BridgeForward Digital Futures")
    client.force_login(user)

    response = client.get(reverse("project-pilot-workspace", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Founding Atlas Partner" in content
    assert "Your pilot command center." in content
    assert "Pilot Checklist" in content
    assert "Snapshot Delivery" in content
    assert "View Snapshot" in content
    assert "Schedule Walkthrough" in content
    assert "Start 30-Day Action Plan" in content


def test_non_member_cannot_view_pilot_workspace(client, pilot_project):
    project, _user = pilot_project
    outsider = get_user_model().objects.create_user(username="pilot-outsider")
    client.force_login(outsider)

    response = client.get(reverse("project-pilot-workspace", kwargs={"pk": project.pk}))

    assert response.status_code == 404


def test_project_member_can_submit_discovery_questionnaire(client, pilot_project):
    project, user = pilot_project
    client.force_login(user)

    response = client.post(
        reverse("project-pilot-questionnaire", kwargs={"pk": project.pk}),
        {
            "organization_name": "BridgeForward Digital Futures",
            "website": "https://bridgeforward.example.org",
            "mission": "Expand digital access and career mobility.",
            "location": "Cleveland, Ohio",
            "year_founded": "2021",
            "annual_budget_range": "$250K - $1M",
            "team_size": "8 staff",
            "primary_programs": "Digital skills, workforce pathways",
            "communities_served": "Youth and young adults",
            "current_initiatives": "Youth technology labs",
            "geographic_reach": "Cleveland and Cuyahoga County",
            "current_revenue_sources": "Foundation grants",
            "grant_experience": "Local and state grants",
            "major_funders": "Community Foundation of Cleveland",
            "fundraising_activities": "Annual campaign",
            "funding_challenges": "Need unrestricted operating support",
            "key_partners": "Community college and public library",
            "community_relationships": "Neighborhood partners",
            "strategic_relationships": "Workforce board",
            "government_relationships": "City youth services",
            "corporate_relationships": "Technology employers",
            "top_goals": "Grow digital equity programs",
            "biggest_challenges": "Capacity and documentation",
            "desired_outcomes": "More youth placed in jobs",
            "success_definition": "Clear 30-day action plan",
            "document_notes": "Strategic plan will be shared later.",
        },
    )

    profile = PilotProfile.objects.get(project=project)
    assert response.status_code == 302
    assert response.url == reverse("project-pilot-workspace", kwargs={"pk": project.pk})
    assert profile.lifecycle_status == PilotProfile.LifecycleStatus.QUESTIONNAIRE_COMPLETED
    assert profile.snapshot_status == PilotProfile.SnapshotStatus.REVIEWING_ORGANIZATION
    assert profile.primary_programs == "Digital skills, workforce pathways"
    assert profile.top_goals == "Grow digital equity programs"


def test_project_member_can_submit_pilot_feedback(client, pilot_project):
    project, user = pilot_project
    profile = PilotProfile.objects.create(project=project, organization_name="BridgeForward Digital Futures")
    client.force_login(user)

    response = client.post(
        reverse("project-pilot-feedback", kwargs={"pk": project.pk}),
        {
            "most_valuable": "The Opportunity Web made the growth path clearer.",
            "confusing": "Some terminology needs a lighter explanation.",
            "indispensable": "Snapshot recommendations.",
            "would_recommend": PilotFeedback.Recommendation.YES,
            "additional_feedback": "Keep the founder walkthrough.",
        },
    )

    feedback = PilotFeedback.objects.get(pilot=profile)
    profile.refresh_from_db()
    assert response.status_code == 302
    assert response.url == reverse("project-pilot-workspace", kwargs={"pk": project.pk})
    assert feedback.most_valuable == "The Opportunity Web made the growth path clearer."
    assert profile.lifecycle_status == PilotProfile.LifecycleStatus.PILOT_COMPLETE


def test_dashboard_shows_pilot_banner_for_pilot_project(client, pilot_project):
    project, user = pilot_project
    PilotProfile.objects.create(
        project=project,
        organization_name="BridgeForward Digital Futures",
        lifecycle_status=PilotProfile.LifecycleStatus.SNAPSHOT_IN_PROGRESS,
    )
    client.force_login(user)

    response = client.get(reverse("project-dashboard", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Founding Atlas Partner" in content
    assert "Snapshot In Progress" in content
    assert "Open Partner Workspace" in content
    assert reverse("project-pilot-workspace", kwargs={"pk": project.pk}) in content
