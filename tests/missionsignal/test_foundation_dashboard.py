"""Ecosystem → Foundations tab: IRS-grounded foundation matching, grant
receipts, and the pursue-into-pipeline wiring.

- Matched foundations come from the same performance-guarded pool as matching
  (derived 990-PF foundations prefiltered by focus overlap; demo-guard applies).
- The receipts panel shows actual FoundationGrantPaid rows to organizations
  like this one (exact-name join to the Florida market DB).
- "Pursue" creates ONE project-scoped Opportunity (external_id funder:<pk>)
  at the Pursuing stage and lands the client on the Pipeline board.
"""
import pytest
from django.urls import reverse

from openoutreach.funding.models import FoundationGrantPaid, Funder, Opportunity
from openoutreach.signals.demo import seed_missionsignal_demo

pytestmark = pytest.mark.django_db


@pytest.fixture
def workspace(db):
    user, organization, project = seed_missionsignal_demo()
    organization.county = "Orange"
    organization.save(update_fields=["county"])
    return user, organization, project


@pytest.fixture
def derived_foundation(db):
    return Funder.objects.create(
        name="Sunlit Futures Family Foundation",
        funder_type=Funder.FunderType.FAMILY_FOUNDATION,
        focus_areas=["Youth Development", "Education"],
        geography=["Florida", "Orange"],
        website="https://sunlitfutures.org",
        active=True,
        is_derived=True,
        grant_count=41,
        grants_total_amount=2_100_000,
        verification_status=Funder.VerificationStatus.VERIFIED,
    )


def test_foundations_page_renders_matched_derived_foundation(client, workspace, derived_foundation):
    user, _organization, project = workspace
    client.force_login(user)
    response = client.get(reverse("project-foundations", kwargs={"pk": project.pk}))
    content = response.content.decode()
    assert response.status_code == 200
    assert "Private Foundations" in content
    assert "Sunlit Futures Family Foundation" in content
    assert "IRS-verified" in content
    assert "41 reported grants" in content
    assert "Pursue — add to Pipeline" in content
    # Tab strip: Foundations is the active ecosystem tab
    assert 'aria-current="page"' in content and "Foundations" in content


def test_receipts_panel_shows_grants_to_orgs_like_yours(client, workspace):
    user, _organization, project = workspace
    from openoutreach.signals.models import FloridaOrg
    FloridaOrg.objects.create(
        record_id="fl-test-1", name="BRIGHT PATHS FOR GIRLS INC", county="Orange",
        state="FL", service_area="Youth Development",
    )
    FoundationGrantPaid.objects.create(
        filer_ein="590000001", filer_name="THE ORANGE BLOSSOM FOUNDATION",
        recipient_name="BRIGHT PATHS FOR GIRLS INC", recipient_state="FL",
        amount=25_000, purpose="General support for girls programming",
        tax_year=2025, source_url="https://apps.irs.gov/pub/epostcard/990/xml/2026/test.zip",
        dedup_key="test-grant-1",
    )
    client.force_login(user)
    content = client.get(reverse("project-foundations", kwargs={"pk": project.pk})).content.decode()
    assert "Foundations Funding Organizations Like Yours" in content
    assert "The Orange Blossom Foundation" in content
    assert "Bright Paths For Girls Inc" in content
    assert "$25,000" in content


def test_pursue_creates_pipeline_opportunity_once(client, workspace, derived_foundation):
    user, _organization, project = workspace
    client.force_login(user)
    url = reverse("project-foundation-track", kwargs={"pk": project.pk, "funder_id": derived_foundation.pk})

    response = client.post(url)
    assert response.status_code == 302
    assert response["Location"] == reverse("project-pipeline", kwargs={"pk": project.pk})

    opportunity = Opportunity.objects.get(project=project, external_id=f"funder:{derived_foundation.pk}")
    assert opportunity.lifecycle_status == Opportunity.LifecycleStatus.PURSUING
    assert opportunity.source_type == Opportunity.SourceType.FUNDER
    assert opportunity.lifecycle_status_history  # honest history entry for the jump
    assert opportunity.tasks.exists()  # default tasks seeded for the stage

    # Idempotent — pursuing again never duplicates
    client.post(url)
    assert Opportunity.objects.filter(project=project, external_id=f"funder:{derived_foundation.pk}").count() == 1

    # It shows up on the Pipeline board and the card flips to "In your pipeline"
    pipeline = client.get(reverse("project-pipeline", kwargs={"pk": project.pk})).content.decode()
    assert "Sunlit Futures Family Foundation — Foundation Grant" in pipeline
    foundations_page = client.get(reverse("project-foundations", kwargs={"pk": project.pk})).content.decode()
    assert "In your pipeline" in foundations_page
    assert "Pursue — add to Pipeline" not in foundations_page or foundations_page.count("Pursue — add to Pipeline") < foundations_page.count("funder-card")


def test_non_member_cannot_pursue(client, workspace, derived_foundation):
    _user, _organization, project = workspace
    from django.contrib.auth import get_user_model
    outsider = get_user_model().objects.create_user(username="outsider", password="x")
    client.force_login(outsider)
    response = client.post(
        reverse("project-foundation-track", kwargs={"pk": project.pk, "funder_id": derived_foundation.pk})
    )
    assert response.status_code == 404
    assert not Opportunity.objects.filter(external_id=f"funder:{derived_foundation.pk}").exists()
