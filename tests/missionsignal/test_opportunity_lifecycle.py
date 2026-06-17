import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from openoutreach.funding.models import Opportunity
from openoutreach.signals.demo import seed_missionsignal_demo
from openoutreach.signals.lifecycle import build_lifecycle_summary, recommended_lifecycle_action


pytestmark = pytest.mark.django_db


@pytest.fixture
def lifecycle_project(db):
    user, _organization, project = seed_missionsignal_demo()
    opportunity = Opportunity.objects.get(name="Digital Equity Grant")
    opportunity.lifecycle_status = Opportunity.LifecycleStatus.QUALIFIED
    opportunity.lifecycle_notes = "Ready for program alignment review."
    opportunity.save(update_fields=["lifecycle_status", "lifecycle_notes", "updated_at"])
    Opportunity.objects.filter(name="Workforce Development Grant").update(
        lifecycle_status=Opportunity.LifecycleStatus.PURSUING,
    )
    Opportunity.objects.filter(name="Youth Technology Initiative").update(
        lifecycle_status=Opportunity.LifecycleStatus.SUBMITTED,
    )
    Opportunity.objects.filter(name="Community Partnership Program").update(
        lifecycle_status=Opportunity.LifecycleStatus.AWARDED,
    )
    return project, user


def test_lifecycle_status_can_move_between_stages(lifecycle_project):
    opportunity = Opportunity.objects.get(name="Digital Equity Grant")

    assert opportunity.lifecycle_status == Opportunity.LifecycleStatus.QUALIFIED
    opportunity.lifecycle_status = Opportunity.LifecycleStatus.PURSUING
    opportunity.save(update_fields=["lifecycle_status", "updated_at"])
    opportunity.refresh_from_db()

    assert opportunity.lifecycle_status == Opportunity.LifecycleStatus.PURSUING
    assert recommended_lifecycle_action(opportunity.lifecycle_status) == "Assign owner and collect requirements"


def test_project_member_can_view_pipeline(client, lifecycle_project):
    project, user = lifecycle_project
    client.force_login(user)

    response = client.get(reverse("project-pipeline", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Opportunity Lifecycle V2" in content
    assert "Opportunity Pipeline" in content
    assert "Lifecycle Board" in content
    assert "Operating Focus" in content
    assert "Discovered" in content
    assert "Reviewing" in content
    assert "Qualified" in content
    assert "Pursuing" in content
    assert "Application Drafting" in content
    assert "Submitted" in content
    assert "Awarded" in content
    assert "Declined" in content
    assert "Closed" in content
    assert "Current Lifecycle Status" in content
    assert "Status History" in content
    assert "Last Updated" in content
    assert "Recommended Next Step" in content
    assert "Assigned Owner" in content
    assert "Assigned Owner: Unassigned" in content
    assert "Lifecycle Notes" in content
    assert "Eligibility Notes" in content
    assert "Focus Areas" in content
    assert "Beneficiaries" in content
    assert "Match Reasons" in content
    assert "Missing Factors" in content
    assert "Improvement Opportunities" in content
    assert "View Details" in content
    assert "Match" in content
    assert "Identify program alignment" in content
    assert "Review eligibility." in content
    assert "Check geography fit." in content
    assert "Assign internal owner." in content
    assert "Track follow-up date." in content


def test_non_member_cannot_view_pipeline(client, lifecycle_project):
    project, _user = lifecycle_project
    outsider = get_user_model().objects.create_user(username="pipeline-outsider")
    client.force_login(outsider)

    response = client.get(reverse("project-pipeline", kwargs={"pk": project.pk}))

    assert response.status_code == 404


def test_lifecycle_summary_counts(lifecycle_project):
    summary = build_lifecycle_summary()
    counts = {stage.label: stage.count for stage in summary.summary_stages}

    assert counts["Discovered"] >= 1
    assert counts["Qualified"] == 1
    assert counts["Pursuing"] == 1
    assert counts["Submitted"] == 1
    assert counts["Awarded"] == 1
    assert summary.active_opportunities >= 4
    assert summary.submitted_opportunities == 1
    assert summary.awarded_opportunities == 1
    assert summary.highest_priority_active_opportunity is not None
