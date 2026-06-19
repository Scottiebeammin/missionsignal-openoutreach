import pytest
from django.urls import reverse

from openoutreach.signals.demo import seed_missionsignal_demo
from openoutreach.signals.workflow import build_workflow_guidance


pytestmark = pytest.mark.django_db


@pytest.fixture
def workflow_project(db):
    user, _organization, project = seed_missionsignal_demo()
    return project, user


def test_workflow_guidance_builds_operating_model(workflow_project):
    project, _user = workflow_project

    workflow = build_workflow_guidance(project, "prioritize")

    assert [stage.short_label for stage in workflow.stages] == [
        "Understand",
        "Prioritize",
        "Prepare",
        "Connect",
        "Execute",
    ]
    assert workflow.current_stage.label == "Prioritize Opportunities"
    assert workflow.recommended_next_stage.label == "Prepare To Win"
    assert workflow.context_statement == "Prioritize the opportunities most aligned to your mission."
    assert 1 <= len(workflow.next_actions) <= 3


def test_dashboard_renders_workflow_progress(client, workflow_project):
    project, user = workflow_project
    client.force_login(user)

    response = client.get(reverse("project-dashboard", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Workflow Progress" in content
    assert "Understand Your Ecosystem" in content
    assert "Prioritize Opportunities" in content
    assert "Prepare To Win" in content
    assert "Activate Relationships" in content
    assert "Execute Pursuits" in content
    assert "Recommended Next Action" in content


@pytest.mark.parametrize(
    ("route_name", "stage_text", "next_route_name"),
    [
        ("project-opportunity-web", "Understand the ecosystem around your mission.", "project-opportunities"),
        ("project-snapshot", "Understand the ecosystem around your mission.", "project-opportunities"),
        ("project-opportunities", "Prioritize the opportunities most aligned to your mission.", "project-readiness"),
        ("project-readiness", "Prepare your organization to pursue opportunities successfully.", "project-relationships"),
        ("project-relationships", "Activate the people and organizations that can accelerate your mission.", "project-pipeline"),
        ("project-pipeline", "Manage active pursuits and execution.", "project-snapshot"),
        ("project-discovery", "Prioritize the opportunities most aligned to your mission.", "project-readiness"),
        ("project-matches", "Prioritize the opportunities most aligned to your mission.", "project-readiness"),
        ("project-documents", "Prepare your organization to pursue opportunities successfully.", "project-relationships"),
        ("project-evidence", "Prepare your organization to pursue opportunities successfully.", "project-relationships"),
    ],
)
def test_workflow_pages_render_orientation_and_next_links(
    client, workflow_project, route_name, stage_text, next_route_name,
):
    project, user = workflow_project
    client.force_login(user)

    response = client.get(reverse(route_name, kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Workflow Progress" in content
    assert stage_text in content
    assert reverse(next_route_name, kwargs={"pk": project.pk}) in content
