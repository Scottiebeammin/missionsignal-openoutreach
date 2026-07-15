"""purge_demo_opportunities: deletes only placeholder/demo opportunities, never
real ones with a genuine source link."""
import pytest
from django.core.management import call_command

from openoutreach.funding.models import Opportunity

pytestmark = pytest.mark.django_db


def test_purges_demo_keeps_real():
    real = Opportunity.objects.create(name="Real Federal Grant", verification_status="verified",
                                      source_urls=["https://grants.gov/opp/123"])
    demo1 = Opportunity.objects.create(name="Demo A", source_urls=["https://x.example.org/y"])
    demo2 = Opportunity.objects.create(name="Demo B", source_references=[{"source": "Demo opportunity inventory"}])

    call_command("purge_demo_opportunities")

    assert Opportunity.objects.filter(pk=real.pk).exists()          # real kept
    assert not Opportunity.objects.filter(pk__in=[demo1.pk, demo2.pk]).exists()   # demo gone


def test_dry_run_deletes_nothing():
    Opportunity.objects.create(name="Demo", source_urls=["https://x.example.org"])
    call_command("purge_demo_opportunities", "--dry-run")
    assert Opportunity.objects.count() == 1                          # untouched
