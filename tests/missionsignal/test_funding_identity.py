from datetime import timedelta

import pytest
from django.utils import timezone

from openoutreach.core.models import Organization, Project
from openoutreach.funding.identity import (
    build_identity_key,
    canonical_url_identity,
    composite_identity,
    normalize_canonical_url,
)
from openoutreach.funding.models import Funder, FundingSignal
from openoutreach.funding.services import resolve_funding_opportunity
from openoutreach.sources.models import Source, SourceRecord


pytestmark = pytest.mark.django_db


@pytest.fixture
def project():
    organization = Organization.objects.create(
        name="Mission Works", website="https://mission.example.org", mission="Improve mobility.",
    )
    return Project.objects.create(
        organization=organization, name="Primary Initiative", programs="Career training.",
    )


@pytest.fixture
def funder():
    return Funder.objects.create(name="Community Foundation")


def source_record(key, external_id="", canonical_url=""):
    source = Source.objects.create(key=key, name=key.title(), source_type=Source.SourceType.API)
    return SourceRecord.objects.create(
        source=source, external_id=external_id, canonical_url=canonical_url,
    )


def test_same_source_external_id_resolves_existing_opportunity(funder):
    record = source_record("grants-api", external_id="grant-1")
    first, created = resolve_funding_opportunity(source_record=record, title="Youth Grant", funder=funder)
    second, second_created = resolve_funding_opportunity(
        source_record=record, title="Changed Source Title", funder=funder,
    )
    assert created is True
    assert second_created is False
    assert second == first
    assert first.identity_key == build_identity_key(source_key="grants-api", external_id="grant-1", title="Youth Grant")


def test_same_normalized_canonical_url_deduplicates_across_sources(funder):
    first_record = source_record("source-one", external_id="one", canonical_url="HTTPS://FUNDS.EXAMPLE.org/grant/?utm=x")
    second_record = source_record("source-two", external_id="two", canonical_url="https://funds.example.org/grant")
    first, _ = resolve_funding_opportunity(source_record=first_record, title="Youth Grant", funder=funder)
    second, created = resolve_funding_opportunity(source_record=second_record, title="Youth Grant", funder=funder)
    assert created is False
    assert second == first
    assert first.identity_key == canonical_url_identity("https://funds.example.org/grant")


def test_normalized_url_variants_match():
    assert normalize_canonical_url("HTTPS://Example.COM:443/grant/?tracking=1#details") == "https://example.com/grant"
    assert normalize_canonical_url("https://example.com/grant") == "https://example.com/grant"


def test_composite_identity_fallback(funder):
    record = source_record("manual")
    deadline = timezone.now()
    opportunity, _ = resolve_funding_opportunity(
        source_record=record,
        title="Youth Grant",
        funder=funder,
        deadline_at=deadline,
        opportunity_type="program",
    )
    assert opportunity.identity_key == composite_identity(
        funder_name=funder.name, title="Youth Grant", deadline=deadline, opportunity_type="program",
    )


def test_same_title_from_different_funders_remains_separate():
    first_funder = Funder.objects.create(name="First Foundation")
    second_funder = Funder.objects.create(name="Second Foundation")
    first, _ = resolve_funding_opportunity(
        source_record=source_record("manual-one"), title="Community Grant", funder=first_funder,
    )
    second, _ = resolve_funding_opportunity(
        source_record=source_record("manual-two"), title="Community Grant", funder=second_funder,
    )
    assert first != second


def test_same_funder_title_with_different_deadlines_remains_separate(funder):
    first, _ = resolve_funding_opportunity(
        source_record=source_record("manual-one"),
        title="Community Grant",
        funder=funder,
        deadline_at=timezone.now(),
    )
    second, _ = resolve_funding_opportunity(
        source_record=source_record("manual-two"),
        title="Community Grant",
        funder=funder,
        deadline_at=timezone.now() + timedelta(days=30),
    )
    assert first != second


def test_one_opportunity_links_to_multiple_sources(funder):
    first_record = source_record("source-one", canonical_url="https://funds.example.org/grant")
    second_record = source_record("source-two", canonical_url="https://funds.example.org/grant/")
    opportunity, _ = resolve_funding_opportunity(source_record=first_record, title="Youth Grant", funder=funder)
    resolve_funding_opportunity(source_record=second_record, title="Youth Grant", funder=funder)
    assert set(opportunity.source_records.all()) == {first_record, second_record}


def test_one_project_receives_one_signal_for_normalized_opportunity(project, funder):
    first_record = source_record("source-one", canonical_url="https://funds.example.org/grant")
    second_record = source_record("source-two", canonical_url="https://funds.example.org/grant/")
    first, _ = resolve_funding_opportunity(source_record=first_record, title="Youth Grant", funder=funder)
    second, _ = resolve_funding_opportunity(source_record=second_record, title="Youth Grant", funder=funder)
    FundingSignal.objects.create(project=project, opportunity=first)
    assert first == second
    assert FundingSignal.objects.filter(project=project, opportunity=second).count() == 1
