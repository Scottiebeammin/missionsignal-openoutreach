import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from openoutreach.funding.models import Opportunity
from openoutreach.signals.demo import seed_missionsignal_demo
from openoutreach.signals.models import OrganizationContact, PartnerOrganization
from openoutreach.signals.relationships import (
    build_opportunity_relationship_context,
    build_relationship_overview,
)


pytestmark = pytest.mark.django_db


@pytest.fixture
def relationship_project(db):
    user, _organization, project = seed_missionsignal_demo()
    return project, user


def test_contact_and_partner_model_behavior(relationship_project):
    project, _user = relationship_project
    contact = OrganizationContact.objects.create(
        project=project,
        name="Avery Grant",
        title="Program Officer",
        organization="Example Foundation",
        contact_type=OrganizationContact.ContactType.PROGRAM_OFFICER,
    )
    partner = PartnerOrganization.objects.create(
        project=project,
        organization_name="Example Community Partner",
        partner_type=PartnerOrganization.PartnerType.COMMUNITY_PARTNER,
    )

    assert str(contact) == "Avery Grant — Example Foundation"
    assert contact.relationship_strength == OrganizationContact.RelationshipStrength.UNKNOWN
    assert contact.status == OrganizationContact.Status.ACTIVE
    assert str(partner) == "Example Community Partner"
    assert partner.relationship_strength == PartnerOrganization.RelationshipStrength.UNKNOWN
    assert partner.status == PartnerOrganization.Status.ACTIVE


def test_relationship_health_scoring_and_demo_records(relationship_project):
    project, _user = relationship_project

    overview = build_relationship_overview(project)

    assert overview.total_contacts >= 6
    assert overview.total_partners >= 5
    assert overview.strong_relationships >= 2
    assert overview.developing_relationships >= 2
    assert overview.active_partner_count >= 5
    assert 0 <= overview.health.score <= 100
    assert overview.health.level in {"Needs Attention", "Developing", "Established", "Strong"}
    assert overview.key_contacts
    assert overview.key_partners
    assert overview.recommended_actions
    assert overview.health.highest_leverage_action


def test_project_member_can_view_relationship_dashboard(client, relationship_project):
    project, user = relationship_project
    client.force_login(user)

    response = client.get(reverse("project-relationships", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Relationship Intelligence V1" in content
    assert "Relationship Dashboard" in content
    assert "Relationship Health" in content
    assert "Relationship Health Transparency" in content
    assert "Score Contributors" in content
    assert "Score Gaps" in content
    assert "Highest Leverage Action" in content
    assert "Total Contacts" in content
    assert "Total Partners" in content
    assert "Strong Relationships" in content
    assert "Developing Relationships" in content
    assert "Key Contacts" in content
    assert "Key Partners" in content
    assert "Relationship Gaps" in content
    assert "Recommended Relationship Actions" in content
    assert "Maya Thompson" in content
    assert "Neighborhood Digital Inclusion Coalition" in content


def test_non_member_cannot_view_relationship_dashboard(client, relationship_project):
    project, _user = relationship_project
    outsider = get_user_model().objects.create_user(username="relationships-outsider")
    client.force_login(outsider)

    response = client.get(reverse("project-relationships", kwargs={"pk": project.pk}))

    assert response.status_code == 404


def test_dashboard_ecosystem_workspace_and_pipeline_show_relationship_context(client, relationship_project):
    project, user = relationship_project
    opportunity = Opportunity.objects.get(name="Digital Equity Grant")
    client.force_login(user)

    dashboard = client.get(reverse("project-dashboard", kwargs={"pk": project.pk})).content.decode()
    ecosystem = client.get(reverse("project-ecosystem", kwargs={"pk": project.pk})).content.decode()
    workspace = client.get(
        reverse("project-opportunity-workspace", kwargs={"pk": project.pk, "opportunity_id": opportunity.pk}),
    ).content.decode()
    pipeline = client.get(reverse("project-pipeline", kwargs={"pk": project.pk})).content.decode()

    assert "Relationship Snapshot" in dashboard
    assert "Relationship Health" in dashboard
    assert reverse("project-relationships", kwargs={"pk": project.pk}) in dashboard
    assert "Relationship Health" in ecosystem
    assert "Contact Count" in ecosystem
    assert "Partner Count" in ecosystem
    assert "Relationship Context" in workspace
    assert "Related Contacts" in workspace
    assert "Related Partners" in workspace
    assert "Known Contact" in pipeline or "Strong Relationship" in pipeline or "Developing Relationship" in pipeline


def test_opportunity_relationship_context_uses_known_relationships(relationship_project):
    project, _user = relationship_project
    opportunity = Opportunity.objects.get(name="Digital Equity Grant")

    context = build_opportunity_relationship_context(project, opportunity)

    assert context.related_contacts
    assert context.related_partners
    assert context.relationship_label in {
        "Known Contact", "Developing Relationship", "Strong Relationship",
    }
    assert context.recommended_action
