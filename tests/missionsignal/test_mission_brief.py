import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from openoutreach.core.models import Organization, Project
from openoutreach.signals.analysis_service import analyze_project


@pytest.fixture
def analyzed_project(db):
    user = get_user_model().objects.create_user(
        username="mission-brief-member",
        password="password",
    )
    organization = Organization.objects.create(
        name="Community Futures",
        website="https://community-futures.example",
        mission="Help youth build careers and thrive in their communities.",
        city="Springfield",
        county="Greene",
        state="Missouri",
        service_area_notes="Serves rural communities throughout the county.",
    )
    project = Project.objects.create(
        organization=organization,
        name="Primary Initiative",
        programs="Career readiness and mentoring programs for youth.",
    )
    project.users.add(user)
    analyze_project(project)
    return project, user


def test_project_member_can_view_mission_brief(client, analyzed_project):
    project, user = analyzed_project
    client.force_login(user)

    response = client.get(reverse("project-mission-brief", kwargs={"pk": project.pk}))

    assert response.status_code == 200


def test_non_member_cannot_view_mission_brief(client, analyzed_project):
    project, _ = analyzed_project
    other_user = get_user_model().objects.create_user(
        username="mission-brief-outsider",
        password="password",
    )
    client.force_login(other_user)

    response = client.get(reverse("project-mission-brief", kwargs={"pk": project.pk}))

    assert response.status_code == 404


def test_mission_brief_displays_profile_funding_criteria_and_next_steps(
    client, analyzed_project
):
    project, user = analyzed_project
    client.force_login(user)

    response = client.get(reverse("project-mission-brief", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert "Community Futures" in content
    assert "Primary Initiative" in content
    assert "Springfield" in content
    assert "Greene" in content
    assert "Missouri" in content
    assert "Serves rural communities throughout the county." in content
    assert "workforce development" in content
    assert "youth" in content
    assert "Executive Snapshot" in content
    assert "Mission Summary" in content
    assert "Organization Identity" in content
    assert "Opportunity Snapshot" in content
    assert "Data Gaps &amp; Warnings" in content
    assert "Recommended Next Actions" in content
    assert "Funding Readiness Profile" in content
    assert "Organization Type" in content
    assert "Budget Range" in content
    assert "Current Funding Sources" in content
    assert "Existing Partnerships" in content
    assert "Program Portfolio" in content
    assert "Preview only" in content
    assert "Analysis Review" in content
    assert "Rerun Analysis" in content
    assert "Start New Intake" in content
    assert "Review and confirm the inferred organization profile." in content
    assert "Prepare outcome and impact data to strengthen funding readiness." in content
    assert "Add a budget range to improve award-size fit." in content
    assert "Add current funding sources to clarify funding history." in content
    assert "Add existing partnerships to support readiness review." in content
    assert "Use the generated funding themes for opportunity discovery." in content


def test_mission_brief_displays_optional_readiness_profile_fields(client, db):
    user = get_user_model().objects.create_user(
        username="mission-brief-readiness",
        password="password",
    )
    organization = Organization.objects.create(
        name="Readiness Works",
        website="https://readiness.example",
        mission="Help youth build careers.",
        organization_type="Nonprofit",
        city="Detroit",
        county="Wayne",
        state="Michigan",
        service_area_notes="Serves neighborhoods across Wayne County.",
        outcomes_and_impact=["85% credential completion", "120 graduates placed"],
        budget_range="$250K - $1M",
        current_funding_sources=["Community Foundation", "City workforce grant"],
        existing_partnerships=["Local College", "Employer Council"],
    )
    project = Project.objects.create(
        organization=organization,
        name="Primary Initiative",
        programs="Career readiness and mentoring programs for youth.",
    )
    project.users.add(user)
    analyze_project(project)
    client.force_login(user)

    response = client.get(reverse("project-mission-brief", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Nonprofit" in content
    assert "Detroit" in content
    assert "Wayne" in content
    assert "Michigan" in content
    assert "85% credential completion, 120 graduates placed" in content
    assert "$250K - $1M" in content
    assert "Community Foundation, City workforce grant" in content
    assert "Local College, Employer Council" in content
    assert "Prepare outcome and impact data" not in content
    assert "Add a budget range" not in content
    assert "Add current funding sources" not in content
    assert "Add existing partnerships" not in content


def test_mission_brief_links_to_future_modules(client, analyzed_project):
    project, user = analyzed_project
    client.force_login(user)

    response = client.get(reverse("project-mission-brief", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert "Programs" in content
    assert "FundingSignal" in content
    assert "PartnershipSignal" in content
    assert "ResourceSignal" in content
    assert reverse("project-programs", kwargs={"pk": project.pk}) in content
    assert reverse("project-funding", kwargs={"pk": project.pk}) in content
    assert reverse("project-partnerships", kwargs={"pk": project.pk}) in content
    assert reverse("project-resources", kwargs={"pk": project.pk}) in content


def test_mission_brief_handles_missing_optional_location_fields(client, db):
    user = get_user_model().objects.create_user(
        username="mission-brief-no-location",
        password="password",
    )
    organization = Organization.objects.create(
        name="No Location Organization",
        website="https://no-location.example",
        mission="Support youth education.",
    )
    project = Project.objects.create(
        organization=organization,
        name="Primary Initiative",
        programs="Education programs for youth.",
    )
    project.users.add(user)
    analyze_project(project)
    client.force_login(user)

    response = client.get(reverse("project-mission-brief", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert response.status_code == 200
    assert "No location context provided." in content
    assert "Confirm service geography to improve local funding matches." in content
    assert "Budget range was not provided." in content
    assert "Current funding sources were not provided." in content
    assert "Existing partnerships were not provided." in content


@pytest.mark.parametrize(
    ("route_name", "module_title", "module_summary"),
    [
        (
            "project-programs",
            "Program Portfolio",
            "portfolio for funder alignment",
        ),
        (
            "project-funding",
            "FundingSignal",
            "Discovery is not enabled yet.",
        ),
        (
            "project-partnerships",
            "PartnershipSignal",
            "Matching logic is not enabled yet.",
        ),
        (
            "project-resources",
            "ResourceSignal",
            "non-funding supports",
        ),
    ],
)
def test_project_member_can_view_placeholder_modules(
    client, analyzed_project, route_name, module_title, module_summary
):
    project, user = analyzed_project
    client.force_login(user)

    response = client.get(reverse(route_name, kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert response.status_code == 200
    assert module_title in content
    assert module_summary in content
    assert "Community Futures" in content
    assert "Primary Initiative" in content
    assert reverse("project-mission-brief", kwargs={"pk": project.pk}) in content


@pytest.mark.parametrize(
    "route_name",
    [
        "project-programs",
        "project-funding",
        "project-partnerships",
        "project-resources",
    ],
)
def test_non_member_cannot_view_placeholder_modules(
    client, analyzed_project, route_name
):
    project, _ = analyzed_project
    other_user = get_user_model().objects.create_user(
        username=f"{route_name}-outsider",
        password="password",
    )
    client.force_login(other_user)

    response = client.get(reverse(route_name, kwargs={"pk": project.pk}))

    assert response.status_code == 404


def test_analysis_detail_links_to_mission_brief(client, analyzed_project):
    project, user = analyzed_project
    client.force_login(user)

    response = client.get(reverse("project-analysis-detail", kwargs={"pk": project.pk}))

    assert response.status_code == 200
    assert (
        reverse("project-mission-brief", kwargs={"pk": project.pk})
        in response.content.decode()
    )
