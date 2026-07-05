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


JOURNEY_DOORS = (
    "project-dashboard",
    "project-snapshot",
    "project-ecosystem",
    "project-opportunities",
    "project-pipeline",
    "project-readiness",
    "project-organization",
)


@pytest.mark.parametrize(
    ("route_name", "hero_text", "door_route", "tab_route"),
    [
        ("project-opportunity-web", "<h1>Opportunity Web</h1>", "project-snapshot", "project-opportunity-web"),
        ("project-snapshot", "Opportunity Web Snapshot", "project-snapshot", "project-snapshot"),
        ("project-opportunities", "Choose what is worth pursuing.", "project-opportunities", "project-opportunities"),
        ("project-readiness", "Prepare to compete.", "project-readiness", "project-readiness"),
        ("project-relationships", "Strengthen the connections that support your mission.", "project-ecosystem", "project-relationships"),
        ("project-pipeline", "Manage active pursuits.", "project-pipeline", None),
        ("project-discovery", "Opportunity Inventory", "project-opportunities", "project-discovery"),
        ("project-matches", "Review pathway fit.", "project-opportunities", "project-matches"),
        ("project-documents", ">Documents</h1>", "project-readiness", "project-documents"),
        ("project-evidence", ">Evidence</h1>", "project-readiness", "project-evidence"),
    ],
)
def test_journey_pages_render_orientation_and_door_navigation(
    client, workflow_project, route_name, hero_text, door_route, tab_route,
):
    """Each journey page orients the user with its hero copy, the active door
    in the 7-door journey sidebar, and (on cluster pages) the active cluster
    tab — and renders every sidebar door for onward navigation. The per-page
    Workflow Progress panel now lives only on the executive dashboard and the
    supporting tools (discovery/matches)."""
    project, user = workflow_project
    client.force_login(user)

    response = client.get(reverse(route_name, kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert response.status_code == 200
    assert hero_text in content
    # The journey sidebar marks this page's door as active...
    door_url = reverse(door_route, kwargs={"pk": project.pk})
    assert f'class="active" href="{door_url}"' in content
    # ...and renders every door for onward navigation.
    for door in JOURNEY_DOORS:
        assert reverse(door, kwargs={"pk": project.pk}) in content
    # Cluster pages mark the current tab (pipeline is a standalone door).
    if tab_route:
        tab_url = reverse(tab_route, kwargs={"pk": project.pk})
        assert f'aria-current="page" href="{tab_url}"' in content


@pytest.mark.parametrize("route_name", ["project-discovery", "project-matches"])
def test_supporting_tools_render_workflow_progress_panel(client, workflow_project, route_name):
    project, user = workflow_project
    client.force_login(user)

    response = client.get(reverse(route_name, kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Workflow Progress" in content
    assert "Choose what is worth pursuing next." in content
    assert reverse("project-readiness", kwargs={"pk": project.pk}) in content
