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
        "Pathways",
        "Prepare",
        "Relationships",
        "Pipeline",
    ]
    assert workflow.current_stage.label == "Choose Strategic Pathways"
    assert workflow.recommended_next_stage.label == "Prepare To Compete"
    assert workflow.context_statement == "Choose what is worth pursuing next."
    assert 1 <= len(workflow.next_actions) <= 3


def test_dashboard_renders_workflow_progress(client, workflow_project):
    project, user = workflow_project
    client.force_login(user)

    response = client.get(reverse("project-dashboard", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Workflow Progress" in content
    assert "Understand Your Ecosystem" in content
    assert "Choose Strategic Pathways" in content
    assert "Prepare To Compete" in content
    assert "Strengthen Relationships" in content
    assert "Manage Active Pursuits" in content
    assert "Recommended Next Action" in content


@pytest.mark.parametrize(
    ("route_name", "stage_text", "next_route_name"),
    [
        ("project-opportunity-web", "Understand the ecosystem around your mission.", "project-opportunities"),
        ("project-snapshot", "Understand the ecosystem around your mission.", "project-opportunities"),
        ("project-opportunities", "Choose what is worth pursuing next.", "project-readiness"),
        ("project-readiness", "Prepare your organization to compete for the right opportunities.", "project-relationships"),
        ("project-relationships", "Strengthen the relationships that support your mission.", "project-pipeline"),
        ("project-pipeline", "Manage active pursuits and execution.", "project-snapshot"),
        ("project-discovery", "Choose what is worth pursuing next.", "project-readiness"),
        ("project-matches", "Choose what is worth pursuing next.", "project-readiness"),
        ("project-documents", "Prepare your organization to compete for the right opportunities.", "project-relationships"),
        ("project-evidence", "Prepare your organization to compete for the right opportunities.", "project-relationships"),
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
