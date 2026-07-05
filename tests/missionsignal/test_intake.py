import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from unittest.mock import patch

from openoutreach.core.models import Organization, OrganizationMember, Project
from openoutreach.signals.forms import OrganizationIntakeForm
from openoutreach.signals.models import OrganizationAnalysisRun


pytestmark = pytest.mark.django_db


VALID_INTAKE_POST = {
    "contact_name": "Jordan Lee",
    "contact_position": "Executive Director",
    "contact_email": "jordan@example.org",
    "organization_name": "Mission Works",
    "website": "https://mission.example.org",
    "mission": "Improve economic mobility.",
    "programs": "Career training.",
    "city": "Detroit",
    "county": "Wayne",
    "state": "MI",
    "focus_area_selections": ["Workforce Development"],
    "beneficiary_selections": ["youth"],
}


@pytest.fixture
def no_background_ingest(monkeypatch):
    """The intake view fires a background Grants.gov/AI research thread —
    stub it out so tests stay offline and deterministic."""
    import openoutreach.signals.research as research

    monkeypatch.setattr(research, "auto_ingest_for_new_project", lambda project: None)


def test_intake_form_fields_and_required_flags():
    form = OrganizationIntakeForm()
    assert list(form.fields) == [
        "contact_name",
        "contact_position",
        "contact_email",
        "organization_name",
        "website",
        "mission",
        "programs",
        "organization_type",
        "city",
        "county",
        "state",
        "service_area_notes",
        "outcomes_and_impact",
        "budget_range",
        "current_funding_sources",
        "existing_partnerships",
        "focus_area_selections",
        "beneficiary_selections",
        "intake_notes",
    ]
    required_fields = [
        "contact_name",
        "contact_position",
        "contact_email",
        "organization_name",
        "website",
        "mission",
        "programs",
        "city",
        "county",
        "state",
        "focus_area_selections",
        "beneficiary_selections",
    ]
    assert all(form.fields[field].required for field in required_fields)
    assert all(
        not form.fields[field].required
        for field in form.fields
        if field not in required_fields
    )


def test_anonymous_intake_redirects_to_login(client):
    response = client.get(reverse("project-intake"))
    assert response.status_code == 302
    assert response.url.startswith("/accounts/login/")


def test_anonymous_intake_post_does_not_create_records(client):
    response = client.post(reverse("project-intake"), VALID_INTAKE_POST)
    assert response.status_code == 302
    assert Organization.objects.count() == 0
    assert Project.objects.count() == 0


def test_intake_page_renders_for_authenticated_user(client):
    user = User.objects.create_user("owner")
    client.force_login(user)
    response = client.get(reverse("project-intake"))
    assert response.status_code == 200
    assert b"Tell us about your organization." in response.content
    assert b"Build my Opportunity Web" in response.content


def test_valid_intake_creates_owned_organization_project_and_analysis_run(
    client, no_background_ingest,
):
    user = User.objects.create_user("owner")
    client.force_login(user)
    response = client.post(reverse("project-intake"), VALID_INTAKE_POST)

    organization = Organization.objects.get()
    project = Project.objects.get()
    run = OrganizationAnalysisRun.objects.get(organization=organization)
    member = OrganizationMember.objects.get(user=user, project=project)
    assert response.status_code == 302
    assert response.url == reverse("project-intake-success", kwargs={"pk": project.pk})
    # Analysis now runs immediately at intake — the org is never left pending.
    assert organization.analysis_status in {
        Organization.AnalysisStatus.READY,
        Organization.AnalysisStatus.PARTIAL,
    }
    assert project.organization == organization
    assert project.name == "Primary Initiative"
    assert list(organization.users.all()) == [user]
    assert list(project.users.all()) == [user]
    assert member.contact_name == "Jordan Lee"
    assert member.contact_position == "Executive Director"
    assert member.contact_email == "jordan@example.org"
    assert member.role == OrganizationMember.Role.OWNER
    assert run.status in {
        OrganizationAnalysisRun.Status.COMPLETED,
        OrganizationAnalysisRun.Status.PARTIAL,
    }
    assert run.input_snapshot["programs"] == "Career training."
    assert organization.city == "Detroit"
    assert organization.county == "Wayne"
    assert organization.state == "MI"
    # Explicit intake selections are stored as authoritative signals.
    assert "Workforce Development" in organization.focus_areas
    assert "youth" in organization.beneficiaries
    # Optional profile fields stay empty when not provided.
    assert organization.organization_type is None
    assert organization.outcomes_and_impact == []
    assert organization.budget_range == ""
    assert organization.current_funding_sources == []
    assert organization.existing_partnerships == []


def test_optional_profile_fields_are_saved_from_intake(client, no_background_ingest):
    user = User.objects.create_user("owner")
    client.force_login(user)
    response = client.post(
        reverse("project-intake"),
        {
            **VALID_INTAKE_POST,
            "organization_type": "Nonprofit",
            "service_area_notes": "Serves Wayne County.",
            "outcomes_and_impact": "85% completion rate\n120 graduates",
            "budget_range": "$250K - $1M",
            "current_funding_sources": "Community Foundation\nCity workforce grant",
            "existing_partnerships": "Local College\nEmployer Council",
        },
    )

    organization = Organization.objects.get()
    run = OrganizationAnalysisRun.objects.get(organization=organization)
    assert response.status_code == 302
    assert organization.organization_type == "Nonprofit"
    assert organization.city == "Detroit"
    assert organization.county == "Wayne"
    assert organization.state == "MI"
    assert organization.service_area_notes == "Serves Wayne County."
    assert organization.outcomes_and_impact == ["85% completion rate", "120 graduates"]
    assert organization.budget_range == "$250K - $1M"
    assert organization.current_funding_sources == [
        "Community Foundation",
        "City workforce grant",
    ]
    assert organization.existing_partnerships == ["Local College", "Employer Council"]
    assert run.input_snapshot["budget_range"] == "$250K - $1M"
    assert run.input_snapshot["existing_partnerships"] == [
        "Local College",
        "Employer Council",
    ]


def test_invalid_intake_does_not_create_partial_project(client):
    user = User.objects.create_user("owner")
    client.force_login(user)
    response = client.post(
        reverse("project-intake"),
        {"organization_name": "Mission Works", "website": "not-a-url", "mission": "", "programs": ""},
    )
    assert response.status_code == 200
    assert Organization.objects.count() == 0
    assert Project.objects.count() == 0
    assert OrganizationAnalysisRun.objects.count() == 0


def test_project_success_is_restricted_to_project_members(client):
    owner = User.objects.create_user("owner")
    outsider = User.objects.create_user("outsider")
    organization = Organization.objects.create(
        name="Mission Works", website="https://mission.example.org", mission="Improve mobility.",
    )
    project = Project.objects.create(
        organization=organization, name="Primary Initiative", programs="Career training.",
    )
    project.users.add(owner)

    client.force_login(outsider)
    assert client.get(reverse("project-intake-success", kwargs={"pk": project.pk})).status_code == 404

    client.force_login(owner)
    assert client.get(reverse("project-intake-success", kwargs={"pk": project.pk})).status_code == 200


def test_intake_rolls_back_when_analysis_run_creation_fails(client, no_background_ingest):
    user = User.objects.create_user("owner")
    client.force_login(user)
    with patch(
        "openoutreach.signals.services.OrganizationAnalysisRun.objects.create",
        side_effect=RuntimeError("analysis unavailable"),
    ), pytest.raises(RuntimeError, match="analysis unavailable"):
        client.post(reverse("project-intake"), VALID_INTAKE_POST)

    assert Organization.objects.count() == 0
    assert Project.objects.count() == 0
