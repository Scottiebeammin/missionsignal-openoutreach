from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from openoutreach.funding.models import Opportunity, OpportunityDeadline, OpportunityTask
from openoutreach.signals.demo import seed_missionsignal_demo
from openoutreach.signals.opportunity_work import (
    build_deadline_summary,
    build_task_summary,
    ensure_default_tasks,
)


pytestmark = pytest.mark.django_db


@pytest.fixture
def workspace_project(db):
    user, _organization, project = seed_missionsignal_demo()
    opportunity = Opportunity.objects.get(name="Digital Equity Grant")
    return project, user, opportunity


def test_project_member_can_view_opportunity_workspace(client, workspace_project):
    project, user, opportunity = workspace_project
    client.force_login(user)

    response = client.get(
        reverse("project-opportunity-workspace", kwargs={"pk": project.pk, "opportunity_id": opportunity.pk}),
    )

    assert response.status_code == 200
    content = response.content.decode()
    assert "Opportunity Workspace V1" in content
    assert "Opportunity Overview" in content
    assert "Match Summary" in content
    assert "Lifecycle Status" in content
    assert "Owner" in content
    assert "Deadline" in content
    assert "Priority" in content
    assert "Recommended Next Step" in content
    assert "Requirements" in content
    assert "Tasks" in content
    assert "Deadlines" in content
    assert "Notes" in content
    assert "History" in content
    assert "Eligibility requirements" in content
    assert "Required documents" in content
    assert "Review eligibility" in content
    assert "Submission deadline" in content


def test_non_member_cannot_view_opportunity_workspace(client, workspace_project):
    project, _user, opportunity = workspace_project
    outsider = get_user_model().objects.create_user(username="workspace-outsider")
    client.force_login(outsider)

    response = client.get(
        reverse("project-opportunity-workspace", kwargs={"pk": project.pk, "opportunity_id": opportunity.pk}),
    )

    assert response.status_code == 404


def test_default_tasks_are_idempotent_and_stage_specific(workspace_project):
    _project, _user, opportunity = workspace_project
    opportunity.lifecycle_status = Opportunity.LifecycleStatus.PURSUING
    opportunity.save(update_fields=["lifecycle_status", "updated_at"])

    first = ensure_default_tasks(opportunity)
    second = ensure_default_tasks(opportunity)
    titles = {task.title for task in second}

    assert len(first) == len(second)
    assert "Collect required documents" in titles
    assert "Prepare budget details" in titles
    assert OpportunityTask.objects.filter(opportunity=opportunity, title="Collect required documents").count() == 1


def test_task_summary_counts_open_complete_blocked_and_overdue(workspace_project):
    _project, _user, opportunity = workspace_project
    task = OpportunityTask.objects.create(
        opportunity=opportunity,
        title="Manual overdue task",
        status=OpportunityTask.Status.BLOCKED,
        priority=OpportunityTask.Priority.HIGH,
        due_date=timezone.localdate() - timedelta(days=1),
    )

    summary = build_task_summary(opportunity)

    assert summary.total_tasks >= 1
    assert summary.open_tasks >= 1
    assert summary.blocked_tasks >= 1
    assert summary.overdue_tasks >= 1
    assert task in summary.tasks


def test_task_status_controls_update_task(client, workspace_project):
    project, user, opportunity = workspace_project
    client.force_login(user)
    task = OpportunityTask.objects.create(opportunity=opportunity, title="Draft narrative")

    response = client.post(
        reverse(
            "project-opportunity-task-status",
            kwargs={"pk": project.pk, "opportunity_id": opportunity.pk, "task_id": task.pk},
        ),
        {"target_status": OpportunityTask.Status.COMPLETE},
    )
    task.refresh_from_db()

    assert response.status_code == 302
    assert response.url == reverse(
        "project-opportunity-workspace", kwargs={"pk": project.pk, "opportunity_id": opportunity.pk},
    )
    assert task.status == OpportunityTask.Status.COMPLETE


def test_deadline_summary_creates_submission_and_internal_review_deadlines(workspace_project):
    _project, _user, opportunity = workspace_project

    summary = build_deadline_summary(opportunity)
    titles = {item.deadline.title for item in summary.deadlines}

    assert "Submission deadline" in titles
    assert "Internal review deadline" in titles
    assert summary.next_deadline is not None
    assert OpportunityDeadline.objects.filter(opportunity=opportunity, title="Submission deadline").count() == 1


def test_dashboard_pipeline_discovery_and_matching_link_to_workspaces(client, workspace_project):
    project, user, opportunity = workspace_project
    client.force_login(user)
    workspace_url = reverse(
        "project-opportunity-workspace", kwargs={"pk": project.pk, "opportunity_id": opportunity.pk},
    )

    discovery = client.get(reverse("project-discovery", kwargs={"pk": project.pk})).content.decode()
    pipeline = client.get(reverse("project-pipeline", kwargs={"pk": project.pk})).content.decode()
    matching = client.get(reverse("project-matches", kwargs={"pk": project.pk})).content.decode()
    dashboard = client.get(reverse("project-dashboard", kwargs={"pk": project.pk})).content.decode()

    assert workspace_url in discovery
    assert workspace_url in pipeline
    assert "Opportunity Workspaces" in matching
    assert workspace_url in matching
    assert "Opportunity Work Summary" in dashboard
    assert "Open Tasks" in dashboard
    assert "Overdue Tasks" in dashboard
    assert "Next Critical Deadline" in dashboard
