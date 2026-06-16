import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from unittest.mock import patch

from openoutreach.core.models import Organization, Project
from openoutreach.signals.forms import OrganizationIntakeForm
from openoutreach.signals.models import OrganizationAnalysisRun


pytestmark = pytest.mark.django_db


def test_intake_form_exposes_only_four_required_fields():
    form = OrganizationIntakeForm()
    assert list(form.fields) == ["organization_name", "website", "mission", "programs"]
    assert all(field.required for field in form.fields.values())


def test_anonymous_intake_redirects_to_login(client):
    response = client.get(reverse("project-intake"))
    assert response.status_code == 302
    assert response.url.startswith("/admin/login/")


def test_anonymous_intake_post_does_not_create_records(client):
    response = client.post(
        reverse("project-intake"),
        {
            "organization_name": "Mission Works",
            "website": "https://mission.example.org",
            "mission": "Improve economic mobility.",
            "programs": "Career training.",
        },
    )
    assert response.status_code == 302
    assert Organization.objects.count() == 0
    assert Project.objects.count() == 0


def test_intake_page_renders_for_authenticated_user(client):
    user = User.objects.create_user("owner")
    client.force_login(user)
    response = client.get(reverse("project-intake"))
    assert response.status_code == 200
    assert b"Analyze Organization" in response.content


def test_valid_intake_creates_owned_organization_project_and_pending_analysis_run(client):
    user = User.objects.create_user("owner")
    client.force_login(user)
    response = client.post(
        reverse("project-intake"),
        {
            "organization_name": "Mission Works",
            "website": "https://mission.example.org",
            "mission": "Improve economic mobility.",
            "programs": "Career training.",
        },
    )

    organization = Organization.objects.get()
    project = Project.objects.get()
    run = OrganizationAnalysisRun.objects.get(organization=organization)
    assert response.status_code == 302
    assert response.url == reverse("project-intake-success", kwargs={"pk": project.pk})
    assert organization.analysis_status == Organization.AnalysisStatus.PENDING
    assert project.organization == organization
    assert project.name == "Primary Initiative"
    assert list(organization.users.all()) == [user]
    assert list(project.users.all()) == [user]
    assert run.status == OrganizationAnalysisRun.Status.PENDING
    assert run.input_snapshot["programs"] == "Career training."


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


def test_intake_rolls_back_when_analysis_run_creation_fails(client):
    user = User.objects.create_user("owner")
    client.force_login(user)
    with patch(
        "openoutreach.signals.services.OrganizationAnalysisRun.objects.create",
        side_effect=RuntimeError("analysis unavailable"),
    ), pytest.raises(RuntimeError, match="analysis unavailable"):
        client.post(
            reverse("project-intake"),
            {
                "organization_name": "Mission Works",
                "website": "https://mission.example.org",
                "mission": "Improve economic mobility.",
                "programs": "Career training.",
            },
        )

    assert Organization.objects.count() == 0
    assert Project.objects.count() == 0
