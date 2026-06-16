import pytest
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.test import RequestFactory
from django.urls import reverse

from openoutreach.core.admin import ProjectAdmin
from openoutreach.core.models import Organization, Project
from openoutreach.funding.models import FundingCriteria


pytestmark = pytest.mark.django_db


@pytest.fixture
def project():
    organization = Organization.objects.create(
        name="Mission Works",
        website="https://mission.example.org",
        mission="Improve economic mobility for youth.",
        city="Detroit",
        state="Michigan",
    )
    return Project.objects.create(
        organization=organization,
        name="Primary Initiative",
        programs="Youth career training and small business coaching.",
    )


def test_member_can_view_analysis_detail(client, project):
    member = User.objects.create_user("member")
    project.users.add(member)
    client.force_login(member)
    response = client.get(reverse("project-analysis-detail", kwargs={"pk": project.pk}))
    assert response.status_code == 200
    assert b"Mission Works" in response.content
    assert b"Run deterministic analysis" in response.content
    assert b"Run analysis to generate FundingCriteria." in response.content


def test_nonmember_cannot_view_or_trigger_analysis(client, project):
    outsider = User.objects.create_user("outsider")
    client.force_login(outsider)
    detail = client.get(reverse("project-analysis-detail", kwargs={"pk": project.pk}))
    trigger = client.post(reverse("run-project-analysis", kwargs={"pk": project.pk}))
    assert detail.status_code == 404
    assert trigger.status_code == 404
    assert FundingCriteria.objects.filter(project=project).count() == 0


def test_member_can_trigger_analysis_and_view_results(client, project):
    member = User.objects.create_user("member")
    project.users.add(member)
    client.force_login(member)
    response = client.post(reverse("run-project-analysis", kwargs={"pk": project.pk}))
    assert response.status_code == 302
    assert response.url == reverse("project-analysis-detail", kwargs={"pk": project.pk})

    detail = client.get(response.url)
    content = detail.content.decode()
    assert detail.status_code == 200
    assert "workforce development" in content
    assert "youth" in content
    assert "Detroit" in content
    assert "Funding Criteria" in content
    assert "government, foundation, corporate" in content
    assert "program grant, general operating support" in content
    assert "Outcomes and impact require supporting evidence" in content


def test_member_can_rerun_analysis_and_refresh_displayed_results(client, project):
    member = User.objects.create_user("member")
    project.users.add(member)
    client.force_login(member)
    trigger_url = reverse("run-project-analysis", kwargs={"pk": project.pk})

    first_response = client.post(trigger_url)
    assert first_response.status_code == 302
    criteria = FundingCriteria.objects.get(project=project)
    first_run_id = criteria.source_analysis_run_id

    project.programs = "Youth career training, food access, and community outreach."
    project.save(update_fields=["programs"])
    second_response = client.post(trigger_url)
    assert second_response.status_code == 302

    criteria.refresh_from_db()
    detail = client.get(reverse("project-analysis-detail", kwargs={"pk": project.pk}))
    content = detail.content.decode()
    assert criteria.source_analysis_run_id != first_run_id
    assert FundingCriteria.objects.filter(project=project).count() == 1
    assert "food security" in content
    assert "community outreach" in content


def test_analysis_trigger_requires_post(client, project):
    member = User.objects.create_user("member")
    project.users.add(member)
    client.force_login(member)
    assert client.get(reverse("run-project-analysis", kwargs={"pk": project.pk})).status_code == 405


def test_admin_action_runs_analysis(project):
    admin_user = User.objects.create_superuser("admin", "admin@example.org", "password")
    request = RequestFactory().post("/admin/core/project/")
    request.user = admin_user

    # Admin actions use the messages framework, which RequestFactory does not install.
    from django.contrib.messages.storage.fallback import FallbackStorage
    request.session = {}
    request._messages = FallbackStorage(request)

    model_admin = ProjectAdmin(Project, admin.site)
    model_admin.run_deterministic_analysis(request, Project.objects.filter(pk=project.pk))

    project.organization.refresh_from_db()
    assert project.organization.organization_summary
    assert FundingCriteria.objects.filter(project=project).exists()
    assert [str(message) for message in get_messages(request)] == ["Analyzed 1 project(s)."]
