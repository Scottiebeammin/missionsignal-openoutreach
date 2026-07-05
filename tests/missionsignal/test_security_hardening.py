"""Cross-tenant and abuse hardening regressions (July 2026 security audit).

- IDOR guard: the pipeline/task mutation endpoints must scope the Opportunity
  to the caller's own project — a member of project A POSTing an opportunity
  id that belongs to project B gets a 404, never a write.
- Referer redirect: the interest toggle follows only same-host referers.
- Password validators: weak passwords are rejected at the public signup form
  (AUTH_PASSWORD_VALIDATORS is populated, so validate_password is not a no-op).
"""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from openoutreach.core.models import Organization, Project
from openoutreach.funding.models import Opportunity, OpportunityTask
from openoutreach.signals.demo import seed_missionsignal_demo

pytestmark = pytest.mark.django_db


@pytest.fixture
def two_tenants(db):
    """User A with their own project, plus a foreign project B holding an opportunity."""
    user_a, _org_a, project_a = seed_missionsignal_demo()
    org_b = Organization.objects.create(name="Other Tenant Org", mission="Other mission.")
    project_b = Project.objects.create(name="Other Tenant Org", organization=org_b)
    opp_b = Opportunity.objects.create(
        project=project_b,
        name="Project B Grant",
        opportunity_type=Opportunity.OpportunityType.GRANT,
        source_type=Opportunity.SourceType.GOVERNMENT,
    )
    return user_a, project_a, opp_b


def test_lifecycle_update_rejects_foreign_opportunity(client, two_tenants):
    user_a, project_a, opp_b = two_tenants
    client.force_login(user_a)
    response = client.post(
        reverse("project-pipeline-lifecycle-update",
                kwargs={"pk": project_a.pk, "opportunity_id": opp_b.pk}),
        {"target_status": Opportunity.LifecycleStatus.REVIEWING},
    )
    assert response.status_code == 404
    opp_b.refresh_from_db()
    assert opp_b.lifecycle_status == Opportunity.LifecycleStatus.DISCOVERED


def test_owner_update_rejects_foreign_opportunity(client, two_tenants):
    user_a, project_a, opp_b = two_tenants
    client.force_login(user_a)
    response = client.post(
        reverse("project-pipeline-owner-update",
                kwargs={"pk": project_a.pk, "opportunity_id": opp_b.pk}),
        {"owner_action": "assign_me"},
    )
    assert response.status_code == 404
    opp_b.refresh_from_db()
    assert opp_b.assigned_owner is None


def test_task_status_update_rejects_foreign_opportunity(client, two_tenants):
    user_a, project_a, opp_b = two_tenants
    task_b = OpportunityTask.objects.create(opportunity=opp_b, title="Draft LOI")
    client.force_login(user_a)
    response = client.post(
        reverse("project-opportunity-task-status",
                kwargs={"pk": project_a.pk, "opportunity_id": opp_b.pk, "task_id": task_b.pk}),
        {"target_status": OpportunityTask.Status.COMPLETE},
    )
    assert response.status_code == 404
    task_b.refresh_from_db()
    assert task_b.status == OpportunityTask.Status.NOT_STARTED


def test_own_project_lifecycle_update_still_works(client, two_tenants):
    user_a, project_a, _opp_b = two_tenants
    opp_a = Opportunity.objects.create(
        project=project_a,
        name="Project A Grant",
        opportunity_type=Opportunity.OpportunityType.GRANT,
        source_type=Opportunity.SourceType.GOVERNMENT,
    )
    client.force_login(user_a)
    response = client.post(
        reverse("project-pipeline-lifecycle-update",
                kwargs={"pk": project_a.pk, "opportunity_id": opp_a.pk}),
        {"target_status": Opportunity.LifecycleStatus.REVIEWING},
    )
    assert response.status_code == 302
    opp_a.refresh_from_db()
    assert opp_a.lifecycle_status == Opportunity.LifecycleStatus.REVIEWING


def test_interest_toggle_ignores_external_referer(client, two_tenants):
    user_a, project_a, _opp_b = two_tenants
    opp_a = Opportunity.objects.create(
        project=project_a,
        name="Project A Grant",
        opportunity_type=Opportunity.OpportunityType.GRANT,
        source_type=Opportunity.SourceType.GOVERNMENT,
    )
    client.force_login(user_a)
    response = client.post(
        reverse("project-opportunity-interest",
                kwargs={"pk": project_a.pk, "opportunity_id": opp_a.pk}),
        HTTP_REFERER="https://evil.example.com/phish",
    )
    assert response.status_code == 302
    assert response["Location"] == reverse("project-opportunities", kwargs={"pk": project_a.pk})


def test_signup_rejects_weak_password(client):
    response = client.post(reverse("signup"), {
        "first_name": "Rae", "email": "rae@weakpass.org",
        "password1": "short1", "password2": "short1",
    })
    assert response.status_code == 200  # form re-rendered with errors
    assert not get_user_model().objects.filter(email="rae@weakpass.org").exists()
