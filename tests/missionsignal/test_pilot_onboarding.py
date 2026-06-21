import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.urls import reverse

from openoutreach.signals.admin import PilotOperationalFilter
from openoutreach.signals.demo import seed_missionsignal_demo
from openoutreach.signals.forms import PilotDiscoveryQuestionnaireForm
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
    assert profile.get_lifecycle_status_display() == "Waitlist"
    assert profile.snapshot_status == PilotProfile.SnapshotStatus.REVIEWING_ORGANIZATION
    assert profile.snapshot_link == ""
    assert profile.walkthrough_status == PilotProfile.WalkthroughStatus.NOT_SCHEDULED
    assert PilotProfile in admin.site._registry
    assert PilotFeedback in admin.site._registry
    pilot_admin = admin.site._registry[PilotProfile]
    assert "lifecycle_status" in pilot_admin.list_filter
    assert PilotOperationalFilter in pilot_admin.list_filter
    assert pilot_admin.list_editable == ("lifecycle_status",)


def test_pilot_admin_command_center_filters_bucket_operational_work(pilot_project):
    project, _user = pilot_project
    active = PilotProfile.objects.create(
        project=project,
        organization_name="Active Pilot",
        lifecycle_status=PilotProfile.LifecycleStatus.ACTIVE_PILOT,
        snapshot_status=PilotProfile.SnapshotStatus.DELIVERED,
        walkthrough_status=PilotProfile.WalkthroughStatus.COMPLETED,
    )
    complete = PilotProfile.objects.create(
        organization_name="Complete Pilot",
        lifecycle_status=PilotProfile.LifecycleStatus.PILOT_COMPLETE,
        snapshot_status=PilotProfile.SnapshotStatus.DELIVERED,
    )
    snapshot_needed = PilotProfile.objects.create(
        organization_name="Snapshot Needed",
        lifecycle_status=PilotProfile.LifecycleStatus.QUESTIONNAIRE_COMPLETED,
        snapshot_status=PilotProfile.SnapshotStatus.REVIEWING_ORGANIZATION,
    )
    walkthrough_needed = PilotProfile.objects.create(
        organization_name="Walkthrough Needed",
        lifecycle_status=PilotProfile.LifecycleStatus.SNAPSHOT_DELIVERED,
        snapshot_status=PilotProfile.SnapshotStatus.DELIVERED,
        walkthrough_status=PilotProfile.WalkthroughStatus.NOT_SCHEDULED,
    )
    PilotFeedback.objects.create(pilot=active, most_valuable="The Snapshot.")
    request = RequestFactory().get("/admin/signals/pilotprofile/")
    model_admin = admin.site._registry[PilotProfile]

    def filtered(value):
        filter_instance = PilotOperationalFilter(
            request,
            {"pilot_command": [value]},
            PilotProfile,
            model_admin,
        )
        return set(filter_instance.queryset(request, PilotProfile.objects.all()))

    assert active in filtered("active")
    assert complete not in filtered("active")
    assert snapshot_needed in filtered("snapshot_needed")
    assert walkthrough_needed in filtered("walkthrough_needed")
    assert walkthrough_needed in filtered("feedback_missing")
    assert active not in filtered("feedback_missing")
    assert complete in filtered("completed")


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


def test_pilot_workspace_displays_delivered_snapshot_link(client, pilot_project):
    project, user = pilot_project
    PilotProfile.objects.create(
        project=project,
        organization_name="BridgeForward Digital Futures",
        snapshot_status=PilotProfile.SnapshotStatus.DELIVERED,
        snapshot_link="https://example.org/bridgeforward-snapshot",
    )
    client.force_login(user)

    response = client.get(reverse("project-pilot-workspace", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert response.status_code == 200
    assert "View Delivered Snapshot" in content
    assert "https://example.org/bridgeforward-snapshot" in content


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


def test_discovery_questionnaire_form_is_mvp_sized():
    form = PilotDiscoveryQuestionnaireForm()

    assert list(form.fields) == [
        "organization_name",
        "website",
        "mission",
        "location",
        "primary_programs",
        "communities_served",
        "current_initiatives",
        "current_revenue_sources",
        "grant_experience",
        "major_funders",
        "key_partners",
        "strategic_relationships",
        "top_goals",
        "biggest_challenges",
        "desired_outcomes",
        "strategic_plan",
        "annual_report",
        "grant_materials",
        "program_information",
        "other_documents",
        "document_notes",
    ]
    assert form.fields["location"].label == "Geography"
    assert form.fields["top_goals"].label == "Top 3 Goals"


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


def test_pilot_feedback_form_uses_mvp_question_labels(client, pilot_project):
    project, user = pilot_project
    PilotProfile.objects.create(project=project, organization_name="BridgeForward Digital Futures")
    client.force_login(user)

    response = client.get(reverse("project-pilot-feedback", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert response.status_code == 200
    assert "What was most valuable?" in content
    assert "What was confusing?" in content
    assert "What would make Anansi Atlas indispensable?" in content
    assert "Would you recommend Anansi Atlas?" in content
    assert "Additional comments" in content


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
