import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from openoutreach.funding.models import (
    DocumentVaultItem,
    EvidenceLibraryItem,
    Opportunity,
    OpportunityDocumentRequirement,
)
from openoutreach.signals.demo import seed_missionsignal_demo
from openoutreach.signals.documents import (
    build_document_evidence_health,
    build_document_vault_summary,
    build_evidence_library_summary,
    build_opportunity_document_summary,
)


pytestmark = pytest.mark.django_db


@pytest.fixture
def document_project(db):
    user, _organization, project = seed_missionsignal_demo()
    return project, user


def test_demo_seed_creates_document_and_evidence_records(document_project):
    project, _user = document_project

    assert DocumentVaultItem.objects.filter(project=project).count() >= 8
    assert EvidenceLibraryItem.objects.filter(project=project).count() >= 8
    assert DocumentVaultItem.objects.filter(project=project, status=DocumentVaultItem.Status.AVAILABLE).exists()
    assert DocumentVaultItem.objects.filter(project=project, status=DocumentVaultItem.Status.MISSING).exists()
    assert EvidenceLibraryItem.objects.filter(project=project, status=EvidenceLibraryItem.Status.AVAILABLE).exists()
    assert EvidenceLibraryItem.objects.filter(project=project, status=EvidenceLibraryItem.Status.MISSING).exists()


def test_document_vault_summary_scores_and_groups(document_project):
    project, _user = document_project

    summary = build_document_vault_summary(project)

    assert summary.total_documents >= 8
    assert summary.available_documents >= 1
    assert summary.missing_documents >= 1
    assert summary.needs_update_documents >= 1
    assert 0 <= summary.readiness_score <= 100
    assert summary.grouped_by_status
    assert summary.grouped_by_type
    assert "Outcome Report" in summary.missing_critical_documents


def test_evidence_library_summary_scores_and_groups(document_project):
    project, _user = document_project

    summary = build_evidence_library_summary(project)

    assert summary.total_evidence_items >= 8
    assert summary.outcome_evidence >= 1
    assert summary.impact_stories >= 1
    assert summary.needs_update_items >= 1
    assert summary.missing_items >= 1
    assert 0 <= summary.readiness_score <= 100
    assert summary.grouped_by_status
    assert summary.grouped_by_type
    assert summary.missing_evidence_items


def test_opportunity_document_requirements_are_idempotent(document_project):
    project, _user = document_project
    opportunity = Opportunity.objects.get(name="Digital Equity Grant")

    first = build_opportunity_document_summary(project, opportunity)
    second = build_opportunity_document_summary(project, opportunity)

    assert len(first.requirements) == len(second.requirements)
    assert OpportunityDocumentRequirement.objects.filter(opportunity=opportunity, title="IRS Determination Letter").count() == 1
    assert OpportunityDocumentRequirement.objects.filter(opportunity=opportunity, title="W-9").count() == 1
    assert first.document_readiness_score >= 0
    assert first.evidence_readiness_score >= 0
    assert first.submission_readiness_score >= 0
    assert first.missing_requirements >= 1


def test_member_can_view_document_vault(client, document_project):
    project, user = document_project
    client.force_login(user)

    response = client.get(reverse("project-documents", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Document Vault V1" in content
    assert "Document readiness score" in content
    assert "Total documents" in content
    assert "Available documents" in content
    assert "Missing documents" in content
    assert "Needs update" in content
    assert "Document List by Status" in content
    assert "IRS Determination Letter" in content


def test_member_can_view_evidence_library(client, document_project):
    project, user = document_project
    client.force_login(user)

    response = client.get(reverse("project-evidence", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Evidence Library V1" in content
    assert "Evidence readiness score" in content
    assert "Total evidence items" in content
    assert "Outcome evidence" in content
    assert "Impact stories" in content
    assert "Evidence List by Status" in content
    assert "Participants completing digital skills workshops" in content


def test_non_member_cannot_view_document_or_evidence_pages(client, document_project):
    project, _user = document_project
    outsider = get_user_model().objects.create_user(username="document-outsider")
    client.force_login(outsider)

    assert client.get(reverse("project-documents", kwargs={"pk": project.pk})).status_code == 404
    assert client.get(reverse("project-evidence", kwargs={"pk": project.pk})).status_code == 404


def test_opportunity_workspace_shows_documents_and_evidence(client, document_project):
    project, user = document_project
    opportunity = Opportunity.objects.get(name="Digital Equity Grant")
    client.force_login(user)

    response = client.get(
        reverse("project-opportunity-workspace", kwargs={"pk": project.pk, "opportunity_id": opportunity.pk}),
    )
    content = response.content.decode()

    assert "Documents" in content
    assert "Evidence" in content
    assert "Required Document" in content or "Required documents" in content
    assert "Required Evidence" in content
    assert "Document readiness score" in content
    assert "Evidence readiness score" in content
    assert "Submission Readiness Impact" in content
    assert "IRS Determination Letter" in content
    assert "Outcome Report" in content


def test_dashboard_pipeline_discovery_matching_show_document_context(client, document_project):
    project, user = document_project
    client.force_login(user)

    dashboard = client.get(reverse("project-dashboard", kwargs={"pk": project.pk})).content.decode()
    pipeline = client.get(reverse("project-pipeline", kwargs={"pk": project.pk})).content.decode()
    discovery = client.get(reverse("project-discovery", kwargs={"pk": project.pk})).content.decode()
    matching = client.get(reverse("project-matches", kwargs={"pk": project.pk})).content.decode()

    assert "Document / Evidence Summary" in dashboard
    assert "Missing critical documents" in dashboard
    assert "Opportunities blocked by missing documents" in dashboard
    assert "Docs Ready" in pipeline
    assert "Docs Missing" in pipeline
    assert "Evidence Missing" in pipeline
    assert "Submission Readiness" in discovery
    assert "Document readiness" in matching
    assert "Evidence readiness" in matching
    assert "Submission readiness" in matching


def test_document_evidence_health_counts_blocked_opportunities(document_project):
    project, _user = document_project

    health = build_document_evidence_health(project)

    assert health.document_summary.total_documents >= 8
    assert health.evidence_summary.total_evidence_items >= 8
    assert health.opportunities_blocked_by_missing_documents >= 1
