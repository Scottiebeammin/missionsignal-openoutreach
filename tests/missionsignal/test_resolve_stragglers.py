"""resolve_warm_stragglers: the 8 curated unmatched warm emails — CC-merge 2
(keep both contacts), create 6 — using the committed day-file drafts."""
import pytest
from django.core.management import call_command

from openoutreach.signals.models import SalesLead

pytestmark = pytest.mark.django_db


def test_cc_merge_keeps_both_contacts_and_creates_missing():
    # Pre-existing leads under the OTHER contact (as in production).
    SalesLead.objects.create(name="Jeans Santiago", organization="8cents",
                             email="jsantiago@8cents.org", list_segment="warm", warmth="warm")
    SalesLead.objects.create(name="Jelani Byron", organization="4cflorida",
                             email="jbyron@4cflorida.org", list_segment="warm", warmth="warm")

    call_command("resolve_warm_stragglers")

    # 8 Cents: primary = who the email addresses, CC = the original lead contact.
    eight = SalesLead.objects.get(email="info@8cents.org")
    assert eight.name == "Lashea Reaves"
    assert eight.cc_emails == "jsantiago@8cents.org"
    assert eight.outreach_draft  # real draft attached
    # 4C likewise
    fourc = SalesLead.objects.get(email="avargas@4cflorida.org")
    assert fourc.cc_emails == "jbyron@4cflorida.org"

    # 6 created leads exist with their real drafts.
    for email in ["dofsowitz@hcc-offm.org", "kelly.astro@hfuw.org", "msperzel@harborhousefl.com",
                  "info@centralfloridachildrenshome.com", "mstahlman@mhacf.org", "erushlow@rmhccf.org"]:
        lead = SalesLead.objects.get(email=email, list_segment="warm")
        assert lead.outreach_draft

    # Idempotent — a second run doesn't duplicate.
    before = SalesLead.objects.count()
    call_command("resolve_warm_stragglers")
    assert SalesLead.objects.count() == before
