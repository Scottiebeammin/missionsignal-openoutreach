from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.db import IntegrityError

from openoutreach.core.models import Campaign, Organization, Project
from openoutreach.funding.models import (
    Funder,
    FundingCriteria,
    FundingOpportunity,
    FundingSignal,
    FundingSignalFeedback,
    default_scoring_weights,
)
from openoutreach.signals.models import OrganizationAnalysisRun, OrganizationSourcePage
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


def test_organization_analysis_run_records_snapshots(organization):
    run = OrganizationAnalysisRun.objects.create(
        organization=organization,
        input_snapshot={"mission": organization.mission},
        output_snapshot={"focus_areas": ["workforce development"]},
    )
    assert run.status == OrganizationAnalysisRun.Status.PENDING
    assert run.output_snapshot["focus_areas"] == ["workforce development"]


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
    funder = Funder.objects.create(name="Community Foundation", funder_type=Funder.FunderType.FOUNDATION)
    assert str(funder) == "Community Foundation"
    assert funder.geography == []


def test_funding_opportunity_tracks_normalized_details(source):
    record = SourceRecord.objects.create(source=source, external_id="grant-3")
    funder = Funder.objects.create(name="Public Fund", funder_type=Funder.FunderType.GOVERNMENT)
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
