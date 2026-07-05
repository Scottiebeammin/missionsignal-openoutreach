"""seed_egi management command: production-safe scoping.

The retired repo-root one-off wiped GLOBAL tables (all funders, all projects'
opportunities) and renamed whatever organization happened to be first. The
command must never do either: other tenants' rows and 990-PF derived funders
survive a run, and only an org actually named like "Empowered Girls" (or an
explicit --organization-id) is touched.
"""
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from openoutreach.core.models import Organization, Project
from openoutreach.funding.models import Funder, Opportunity
from openoutreach.signals.models import PilotProfile

pytestmark = pytest.mark.django_db


@pytest.fixture
def other_tenant(db):
    org = Organization.objects.create(name="Other Tenant Org", mission="Other mission.")
    project = Project.objects.create(name="Other Tenant", organization=org)
    opportunity = Opportunity.objects.create(
        project=project,
        name="Foreign Grant",
        opportunity_type=Opportunity.OpportunityType.GRANT,
        source_type=Opportunity.SourceType.GOVERNMENT,
    )
    return org, project, opportunity


def test_seed_creates_egi_workspace_and_preserves_other_tenants(other_tenant):
    other_org, _other_project, foreign_opp = other_tenant
    derived = Funder.objects.create(name="Some 990-PF Foundation", is_derived=True, active=True)

    call_command("seed_egi")

    egi_org = Organization.objects.get(name="Empowered Girls Inc.")
    egi_project = Project.objects.get(organization=egi_org)
    assert Opportunity.objects.filter(project=egi_project).count() >= 10
    assert PilotProfile.objects.filter(project=egi_project).count() == 1

    # Global tables were upserted, never wiped
    assert Funder.objects.filter(pk=derived.pk).exists()
    # Other tenant untouched — rows survive, org was not renamed/hijacked
    assert Opportunity.objects.filter(pk=foreign_opp.pk).exists()
    other_org.refresh_from_db()
    assert other_org.name == "Other Tenant Org"


def test_seed_is_idempotent_upserts_not_duplicates(other_tenant):
    call_command("seed_egi")
    funder_count = Funder.objects.count()
    egi_project = Project.objects.get(organization__name="Empowered Girls Inc.")
    ingested = Opportunity.objects.create(
        project=egi_project,
        name="Ingested Federal Grant",
        external_id="grants.gov:999999",
        opportunity_type=Opportunity.OpportunityType.GRANT,
        source_type=Opportunity.SourceType.GOVERNMENT,
    )

    call_command("seed_egi")

    assert Funder.objects.count() == funder_count  # upserted by name, no dupes
    assert PilotProfile.objects.filter(project=egi_project).count() == 1
    # Ingested (grants.gov) opportunities survive the project reset
    assert Opportunity.objects.filter(pk=ingested.pk).exists()
    assert Organization.objects.filter(name="Empowered Girls Inc.").count() == 1


def test_ambiguous_match_requires_explicit_id(other_tenant):
    Organization.objects.create(name="Empowered Girls Inc.", mission="A")
    Organization.objects.create(name="Empowered Girls Foundation", mission="B")
    with pytest.raises(CommandError, match="organization-id"):
        call_command("seed_egi")
