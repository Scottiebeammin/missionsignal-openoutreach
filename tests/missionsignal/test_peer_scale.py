""""Orgs like yours" must mean like yours in SCALE, not just sector — a $350M
university and a $29k all-volunteer nonprofit are both tagged "Education"."""
import pytest

from openoutreach.signals.foundations import budget_target_amount, peer_income_ceiling

pytestmark = pytest.mark.django_db


def test_micro_org_band_targets_small_grants():
    # A ~$29k all-volunteer org: a $25k ask is most of their year — target ~$5k.
    assert budget_target_amount("under_50k") == 5_000
    assert budget_target_amount("under_250k") == 25_000          # existing band unchanged


def test_peer_ceiling_scales_with_budget():
    assert peer_income_ceiling("under_50k") == 1_000_000          # excludes the $350M university
    assert peer_income_ceiling("under_250k") == 5_000_000
    assert peer_income_ceiling("1m-5m") == 100_000_000
    assert peer_income_ceiling("") is None                        # unknown budget → no ceiling


def test_grants_to_orgs_like_keeps_unknown_income_but_drops_giants():
    from openoutreach.funding.models import FoundationGrantPaid
    from openoutreach.signals.models import FloridaOrg

    FloridaOrg.objects.create(record_id="A", name="Tiny Youth Org", service_area="Education",
                              county="Orange", income_amount=40_000)
    FloridaOrg.objects.create(record_id="B", name="Big University", service_area="Education",
                              county="Orange", income_amount=350_000_000)
    FloridaOrg.objects.create(record_id="C", name="Unknown Size Org", service_area="Education",
                              county="Orange", income_amount=None)
    for i, nm in enumerate(("Tiny Youth Org", "Big University", "Unknown Size Org")):
        FoundationGrantPaid.objects.create(filer_ein=f"1{i}", recipient_name=nm, amount=5000,
                                           dedup_key=f"peer-scale-test-{i}")

    got = {g.recipient_name for g in
           FoundationGrantPaid.grants_to_orgs_like("Education", county="Orange", max_income=1_000_000)}
    assert "Tiny Youth Org" in got          # a real peer
    assert "Unknown Size Org" in got        # 990-N filers report no income — keep them
    assert "Big University" not in got      # $350M is not "an org like yours"
