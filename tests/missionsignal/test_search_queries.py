import pytest
from django.db import IntegrityError, transaction

from openoutreach.core.models import Organization, Project
from openoutreach.sources.hashing import canonicalize_filters, hash_filters
from openoutreach.sources.models import SearchQuery, Source


pytestmark = pytest.mark.django_db


@pytest.fixture
def project():
    organization = Organization.objects.create(
        name="Mission Works",
        website="https://mission.example.org",
        mission="Improve economic mobility.",
    )
    return Project.objects.create(
        organization=organization,
        name="Primary Initiative",
        programs="Career training.",
    )


@pytest.fixture
def source():
    return Source.objects.create(key="manual", name="Manual", source_type=Source.SourceType.MANUAL)


def create_query(project, source, filters):
    return SearchQuery.objects.create(
        project=project,
        source=source,
        query="workforce grants",
        filters=filters,
    )


def test_empty_filters_have_canonical_hash(project, source):
    query = create_query(project, source, {})
    assert canonicalize_filters({}) == "{}"
    assert query.filters_hash == hash_filters({})
    assert len(query.filters_hash) == 64


def test_same_filters_with_different_key_order_have_same_hash(project, source):
    first = create_query(project, source, {"state": "MI", "status": "open"})
    assert first.filters_hash == hash_filters({"status": "open", "state": "MI"})


def test_different_filters_have_different_hashes(project, source):
    first = create_query(project, source, {"state": "MI"})
    second = create_query(project, source, {"state": "OH"})
    assert first.filters_hash != second.filters_hash


def test_nested_filters_are_canonicalized(project, source):
    filters = {"eligibility": {"types": ["nonprofit", "school"], "active": True}}
    query = create_query(project, source, filters)
    assert query.filters_hash == hash_filters(filters)


def test_unicode_values_are_hashed_deterministically(project, source):
    filters = {"service_area": "Montréal", "focus": "éducation"}
    query = create_query(project, source, filters)
    assert "Montréal" in canonicalize_filters(filters)
    assert query.filters_hash == hash_filters(filters)


def test_filters_hash_updates_when_filters_change(project, source):
    query = create_query(project, source, {"state": "MI"})
    original_hash = query.filters_hash
    query.filters = {"state": "OH"}
    query.save(update_fields=["filters"])
    query.refresh_from_db()
    assert query.filters_hash == hash_filters({"state": "OH"})
    assert query.filters_hash != original_hash


def test_generated_filters_hash_prevents_duplicate_queries(project, source):
    create_query(project, source, {"state": "MI", "status": "open"})
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            create_query(project, source, {"status": "open", "state": "MI"})
