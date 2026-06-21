from decimal import Decimal

import pytest
from django.contrib import admin
from django.contrib.auth.models import User
from django.db import IntegrityError

from openoutreach.core.models import Campaign, Organization, Project
from openoutreach.funding.models import (
    DocumentVaultItem,
    EvidenceLibraryItem,
    Funder,
    FundingCriteria,
    FundingOpportunity,
    FundingSignal,
    FundingSignalFeedback,
    GovernmentEntity,
    Opportunity,
    OpportunityDeadline,
    OpportunityDocumentRequirement,
    OpportunityTask,
    PartnerOrganization,
    ResourceProvider,
    SourceOrganization,
    default_scoring_weights,
)
from openoutreach.signals.models import Celebration, InterestSignup, OrganizationAnalysisRun, OrganizationSourcePage
from openoutreach.signals.models import OrganizationContact, PartnerOrganization as RelationshipPartnerOrganization
from openoutreach.sources.models import SearchQuery, Source, SourceRecord


pytestmark = pytest.mark.django_db


@pytest.fixture
def organization():
    return Organization.objects.create(
        name="Mission Works",
        website="https://mission.example.org",
        mission="Improve economic mobility.",
        city="Detroit",
        county="Wayne",
        state="Michigan",
        service_area_notes="Serves Wayne County.",
    )


@pytest.fixture
def project(organization):
    return Project.objects.create(
        organization=organization,
        name="Primary Initiative",
        programs="Career training and small business coaching.",
    )


@pytest.fixture
def source():
    return Source.objects.create(key="manual", name="Manual", source_type=Source.SourceType.MANUAL)


def test_organization_has_analyzer_first_defaults_and_optional_location_fields(organization):
    assert organization.analysis_status == Organization.AnalysisStatus.PENDING
    assert organization.focus_areas == []
    assert organization.analysis_confidence is None
    assert organization.city == "Detroit"
    assert organization.county == "Wayne"
    assert organization.state == "Michigan"
    assert organization.service_area_notes == "Serves Wayne County."
    assert organization.budget_range == ""
    assert organization.current_funding_sources == []
    assert organization.existing_partnerships == []
    assert str(organization) == "Mission Works"


def test_project_is_an_organization_initiative_and_campaign_remains_functional(project, organization):
    assert project.organization == organization
    assert project.name == "Primary Initiative"
    assert str(project) == "Mission Works — Primary Initiative"
    assert Campaign.objects.create(name="Legacy Campaign").pk


def test_organization_can_have_multiple_projects(organization):
    Project.objects.create(organization=organization, name="Primary Initiative", programs="Training")
    Project.objects.create(organization=organization, name="Capital Initiative", programs="Facilities")
    assert list(organization.projects.values_list("name", flat=True)) == [
        "Primary Initiative",
        "Capital Initiative",
    ]


def test_organization_and_project_users_relationship(project, organization):
    user = User.objects.create_user("analyst")
    organization.users.add(user)
    project.users.add(user)
    assert list(user.missionsignal_organizations.all()) == [organization]
    assert list(user.missionsignal_projects.all()) == [project]


def test_organization_source_page_is_unique_per_organization_and_url(organization):
    OrganizationSourcePage.objects.create(
        organization=organization, url="https://mission.example.org/about",
    )
    with pytest.raises(IntegrityError):
        OrganizationSourcePage.objects.create(
            organization=organization, url="https://mission.example.org/about",
        )


def test_organization_source_page_supports_manual_research_notes(project, organization):
    first = OrganizationSourcePage.objects.create(
        organization=organization,
        project=project,
        title="County workforce notes",
        source_type=OrganizationSourcePage.SourceType.FUNDER_RESEARCH,
        notes="Local workforce funder appears aligned with career training.",
        raw_text="Eligibility notes and staff observations.",
        relevance=OrganizationSourcePage.Relevance.HIGH,
        review_status=OrganizationSourcePage.ReviewStatus.REVIEWED,
    )
    second = OrganizationSourcePage.objects.create(
        organization=organization,
        project=project,
        title="Partner landscape notes",
        source_type=OrganizationSourcePage.SourceType.PARTNER_RESEARCH,
    )

    assert first.url == ""
    assert str(first) == "County workforce notes"
    assert second.url == ""
    assert first.project == project


def test_organization_analysis_run_records_snapshots(organization):
    run = OrganizationAnalysisRun.objects.create(
        organization=organization,
        input_snapshot={"mission": organization.mission},
        output_snapshot={"focus_areas": ["workforce development"]},
    )
    assert run.status == OrganizationAnalysisRun.Status.PENDING
    assert run.output_snapshot["focus_areas"] == ["workforce development"]


def test_celebration_model_defaults_and_string(project):
    celebration = Celebration.objects.create(
        project=project,
        title="Community Milestone",
        celebration_type=Celebration.CelebrationType.IMPACT_MILESTONE,
        description="A meaningful program milestone was documented.",
        impact="The milestone gives the team a clearer story of mission progress.",
    )
    assert str(celebration) == "Community Milestone"
    assert celebration.organization_name == ""
    assert celebration.website == ""
    assert celebration.celebration_type == Celebration.CelebrationType.IMPACT_MILESTONE


def test_interest_signup_model_defaults_and_string():
    signup = InterestSignup.objects.create(
        name="Jordan Lee",
        organization="Mission Works",
        email="jordan@example.org",
        interest_type=InterestSignup.InterestType.OPPORTUNITY_WEB_SNAPSHOT,
    )

    assert str(signup) == "Mission Works — jordan@example.org"
    assert signup.status == InterestSignup.Status.NEW
    assert signup.role == ""
    assert signup.website == ""
    assert signup.message == ""


def test_relationship_contact_model_defaults_and_string(project):
    contact = OrganizationContact.objects.create(
        project=project,
        name="Avery Grant",
        organization="Example Foundation",
        contact_type=OrganizationContact.ContactType.PROGRAM_OFFICER,
    )
    assert str(contact) == "Avery Grant — Example Foundation"
    assert contact.status == OrganizationContact.Status.ACTIVE
    assert contact.relationship_strength == OrganizationContact.RelationshipStrength.UNKNOWN
    assert contact.email == ""
    assert contact.phone == ""


def test_relationship_partner_model_defaults_and_string(project):
    partner = RelationshipPartnerOrganization.objects.create(
        project=project,
        organization_name="Example Partner",
        partner_type=RelationshipPartnerOrganization.PartnerType.COMMUNITY_PARTNER,
    )
    assert str(partner) == "Example Partner"
    assert partner.status == RelationshipPartnerOrganization.Status.ACTIVE
    assert partner.relationship_strength == RelationshipPartnerOrganization.RelationshipStrength.UNKNOWN
    assert partner.website == ""


def test_funding_criteria_defaults_and_one_per_project(project):
    criteria = FundingCriteria.objects.create(project=project)
    assert criteria.deadline_horizon_days == 365
    assert criteria.scoring_weights == default_scoring_weights()
    with pytest.raises(IntegrityError):
        FundingCriteria.objects.create(project=project)


def test_source_model(source):
    assert source.active is True
    assert source.configuration == {}
    assert str(source) == "Manual"


def test_search_query_is_project_source_and_filter_hash_unique(project, source):
    SearchQuery.objects.create(project=project, source=source, query="youth workforce grants")
    with pytest.raises(IntegrityError):
        SearchQuery.objects.create(project=project, source=source, query="youth workforce grants")


@pytest.mark.django_db(transaction=True)
def test_source_record_external_id_and_canonical_url_deduplication(source):
    SourceRecord.objects.create(source=source, external_id="grant-1", title="Grant One")
    with pytest.raises(IntegrityError):
        SourceRecord.objects.create(source=source, external_id="grant-1")

    SourceRecord.objects.create(source=source, canonical_url="https://funding.example.org/2")
    with pytest.raises(IntegrityError):
        SourceRecord.objects.create(source=source, canonical_url="https://funding.example.org/2")


def test_source_record_can_track_search_queries(project, source):
    query = SearchQuery.objects.create(project=project, source=source, query="economic mobility")
    record = SourceRecord.objects.create(source=source, external_id="grant-2")
    record.search_queries.add(query)
    assert list(query.source_records.all()) == [record]


def test_funder_model():
    funder = Funder.objects.create(
        name="Community Foundation",
        funder_type=Funder.FunderType.COMMUNITY_FOUNDATION,
        focus_areas=["workforce development"],
        beneficiaries=["youth"],
    )
    assert str(funder) == "Community Foundation"
    assert funder.active is True
    assert funder.geography == []
    assert funder.focus_areas == ["workforce development"]
    assert funder.beneficiaries == ["youth"]


def test_government_entity_model_defaults_and_string():
    entity = GovernmentEntity.objects.create(
        name="City Workforce Office",
        entity_type=GovernmentEntity.EntityType.CITY_GOVERNMENT,
        opportunity_lanes=["City Grants", "RFPs / Procurement Opportunities"],
    )
    assert str(entity) == "City Workforce Office"
    assert entity.active is True
    assert entity.geography == []
    assert entity.focus_areas == []
    assert entity.opportunity_lanes == ["City Grants", "RFPs / Procurement Opportunities"]


def test_resource_provider_model_defaults_and_string():
    provider = ResourceProvider.objects.create(
        name="Capacity Lab",
        resource_type=ResourceProvider.ResourceType.CAPACITY_BUILDING_ORGANIZATION,
        resource_categories=["Capacity Building Programs"],
    )
    assert str(provider) == "Capacity Lab"
    assert provider.active is True
    assert provider.geography == []
    assert provider.focus_areas == []
    assert provider.resource_categories == ["Capacity Building Programs"]


def test_partner_organization_model_defaults_and_string():
    partner = PartnerOrganization.objects.create(
        name="Community College Partner",
        partner_type=PartnerOrganization.PartnerType.COMMUNITY_COLLEGE,
        collaboration_opportunities=["credential pathways", "referrals"],
    )
    assert str(partner) == "Community College Partner"
    assert partner.active is True
    assert partner.geography == []
    assert partner.focus_areas == []
    assert partner.collaboration_opportunities == ["credential pathways", "referrals"]


def test_opportunity_model_defaults_and_string():
    opportunity = Opportunity.objects.create(
        name="Digital Equity Grant",
        focus_areas=["digital equity"],
        beneficiaries=["youth"],
    )
    assert str(opportunity) == "Digital Equity Grant"
    assert opportunity.opportunity_type == Opportunity.OpportunityType.GRANT
    assert opportunity.source_type == Opportunity.SourceType.MANUAL
    assert opportunity.status == Opportunity.Status.ACTIVE
    assert opportunity.priority_level == Opportunity.PriorityLevel.MEDIUM
    assert opportunity.estimated_value is None
    assert opportunity.value_confidence == Opportunity.ValueConfidence.MEDIUM
    assert opportunity.forecast_notes == ""
    assert opportunity.lifecycle_status == Opportunity.LifecycleStatus.DISCOVERED
    assert opportunity.assigned_owner is None
    assert opportunity.lifecycle_notes == ""
    assert opportunity.lifecycle_status_history == []
    assert opportunity.source_organization is None
    assert opportunity.deadline is None
    assert opportunity.geography == []
    assert opportunity.focus_areas == ["digital equity"]
    assert opportunity.beneficiaries == ["youth"]


def test_opportunity_task_model_defaults_and_string():
    opportunity = Opportunity.objects.create(name="Digital Equity Grant")
    task = OpportunityTask.objects.create(
        opportunity=opportunity,
        title="Review eligibility",
        description="Check applicant requirements.",
    )

    assert str(task) == "Review eligibility"
    assert task.status == OpportunityTask.Status.NOT_STARTED
    assert task.priority == OpportunityTask.Priority.MEDIUM
    assert task.owner is None
    assert task.due_date is None


def test_opportunity_deadline_model_defaults_and_string():
    opportunity = Opportunity.objects.create(name="Digital Equity Grant")
    deadline = OpportunityDeadline.objects.create(
        opportunity=opportunity,
        title="Submission deadline",
        deadline_date="2026-08-15",
    )

    assert str(deadline) == "Submission deadline"
    assert deadline.deadline_type == OpportunityDeadline.DeadlineType.SUBMISSION
    assert deadline.status == OpportunityDeadline.Status.UPCOMING
    assert deadline.notes == ""


def test_document_vault_item_model_defaults_and_string(project):
    document = DocumentVaultItem.objects.create(project=project, title="W-9")

    assert str(document) == "W-9"
    assert document.document_type == DocumentVaultItem.DocumentType.OTHER
    assert document.status == DocumentVaultItem.Status.MISSING
    assert document.file_reference == ""
    assert document.notes == ""


def test_evidence_library_item_model_defaults_and_string(project):
    evidence = EvidenceLibraryItem.objects.create(project=project, title="Outcome metric")

    assert str(evidence) == "Outcome metric"
    assert evidence.evidence_type == EvidenceLibraryItem.EvidenceType.OTHER
    assert evidence.status == EvidenceLibraryItem.Status.MISSING
    assert evidence.related_program == ""
    assert evidence.metric_name == ""
    assert evidence.metric_value == ""


def test_opportunity_document_requirement_model_defaults_and_string():
    opportunity = Opportunity.objects.create(name="Digital Equity Grant")
    requirement = OpportunityDocumentRequirement.objects.create(
        opportunity=opportunity,
        title="IRS Determination Letter",
    )

    assert str(requirement) == "IRS Determination Letter"
    assert requirement.requirement_type == OpportunityDocumentRequirement.RequirementType.REQUIRED_DOCUMENT
    assert requirement.status == OpportunityDocumentRequirement.Status.MISSING
    assert requirement.linked_document is None
    assert requirement.notes == ""


def test_source_organization_model_defaults_and_string():
    source = SourceOrganization.objects.create(
        name="Community Foundation",
        organization_type=SourceOrganization.OrganizationType.FOUNDATION,
        geography=["Cleveland"],
    )
    assert str(source) == "Community Foundation"
    assert source.active is True
    assert source.website == ""
    assert source.geography == ["Cleveland"]


def test_opportunity_database_models_are_registered_in_admin():
    assert admin.site.is_registered(Funder)
    assert admin.site.is_registered(GovernmentEntity)
    assert admin.site.is_registered(ResourceProvider)
    assert admin.site.is_registered(PartnerOrganization)
    assert admin.site.is_registered(Opportunity)
    assert admin.site.is_registered(OpportunityTask)
    assert admin.site.is_registered(OpportunityDeadline)
    assert admin.site.is_registered(DocumentVaultItem)
    assert admin.site.is_registered(EvidenceLibraryItem)
    assert admin.site.is_registered(OpportunityDocumentRequirement)
    assert admin.site.is_registered(SourceOrganization)
    assert admin.site.is_registered(OrganizationContact)
    assert admin.site.is_registered(RelationshipPartnerOrganization)
    assert admin.site.is_registered(InterestSignup)
    source_admin = admin.site._registry[OrganizationSourcePage]
    assert "source_type" in source_admin.list_filter
    assert "review_status" in source_admin.list_filter
    assert source_admin.list_editable == ("review_status", "relevance")



def test_funding_opportunity_tracks_normalized_details(source):
    record = SourceRecord.objects.create(source=source, external_id="grant-3")
    funder = Funder.objects.create(name="Public Fund", funder_type=Funder.FunderType.LOCAL_GOVERNMENT)
    opportunity = FundingOpportunity.objects.create(
        funder=funder,
        title="Workforce Innovation Grant",
        amount_min=Decimal("10000.00"),
        amount_max=Decimal("50000.00"),
        focus_areas=["workforce development"],
    )
    opportunity.source_records.add(record, through_defaults={"source_external_id": record.external_id})
    assert opportunity.status == FundingOpportunity.Status.UNKNOWN
    assert opportunity.currency == "USD"
    assert opportunity.focus_areas == ["workforce development"]


def test_funding_signal_is_unique_per_project_and_opportunity(project):
    opportunity = FundingOpportunity.objects.create(title="Capacity Grant")
    signal = FundingSignal.objects.create(project=project, opportunity=opportunity, score=84.0)
    assert signal.state == FundingSignal.State.DISCOVERED
    assert signal.eligibility_status == FundingSignal.EligibilityStatus.UNKNOWN
    with pytest.raises(IntegrityError):
        FundingSignal.objects.create(project=project, opportunity=opportunity)


def test_funding_signal_feedback(project):
    opportunity = FundingOpportunity.objects.create(title="Capacity Grant")
    signal = FundingSignal.objects.create(project=project, opportunity=opportunity)
    feedback = FundingSignalFeedback.objects.create(
        signal=signal, label=FundingSignalFeedback.Label.GOOD_FIT, reason="Strong mission alignment",
    )
    assert list(signal.feedback.all()) == [feedback]
    assert "Good Fit" in str(feedback)
