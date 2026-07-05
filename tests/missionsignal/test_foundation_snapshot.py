"""foundation_snapshot export/import: portable, idempotent transfer of the
mined 990-PF grants between environments (dedup_key keyed)."""
import pytest
from django.core.management import call_command

from openoutreach.funding.models import FoundationGrantPaid

pytestmark = pytest.mark.django_db


def _make_grant(key, recipient="BRIGHT PATHS INC", amount=25_000):
    return FoundationGrantPaid.objects.create(
        filer_ein="590000001", filer_name="THE ORANGE BLOSSOM FOUNDATION",
        filer_state="FL", recipient_name=recipient, recipient_state="FL",
        amount=amount, purpose="General support", tax_year=2025,
        source_url="https://apps.irs.gov/pub/epostcard/990/xml/2026/x.zip",
        dedup_key=key,
    )


def test_export_import_round_trip_idempotent(tmp_path):
    snap = str(tmp_path / "grants.csv.gz")
    _make_grant("k-1")
    _make_grant("k-2", recipient="YOUTH FUTURES INC", amount=12_500)

    call_command("foundation_snapshot", "export", "--snapshot", snap)

    # Wipe and restore from the snapshot.
    FoundationGrantPaid.objects.all().delete()
    assert FoundationGrantPaid.objects.count() == 0
    call_command("foundation_snapshot", "import", "--snapshot", snap)
    assert FoundationGrantPaid.objects.count() == 2
    restored = FoundationGrantPaid.objects.get(dedup_key="k-2")
    assert restored.recipient_name == "YOUTH FUTURES INC"
    assert restored.amount == 12_500          # BigIntegerField round-trips as int
    assert restored.tax_year == "2025"        # CharField round-trips as text

    # Re-import is a no-op (dedup_key already present).
    call_command("foundation_snapshot", "import", "--snapshot", snap)
    assert FoundationGrantPaid.objects.count() == 2


def test_import_only_adds_missing(tmp_path):
    snap = str(tmp_path / "grants.csv.gz")
    _make_grant("k-1")
    _make_grant("k-2", recipient="YOUTH FUTURES INC")
    call_command("foundation_snapshot", "export", "--snapshot", snap)

    # k-1 stays; only k-2 is missing → import adds exactly one.
    FoundationGrantPaid.objects.filter(dedup_key="k-2").delete()
    call_command("foundation_snapshot", "import", "--snapshot", snap)
    assert FoundationGrantPaid.objects.count() == 2
    assert FoundationGrantPaid.objects.filter(dedup_key="k-2").exists()
