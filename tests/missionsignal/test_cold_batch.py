"""Junk-email hygiene + the curated cold-outreach batch loader.

- clean_market_emails blanks scraped placeholders/telemetry/own-address so cold
  outreach never sends to a bad address.
- seed_cold_batch promotes the curated orgs: valid-email ones become cockpit
  leads, phone-only keepers land in the pipeline with no email (junk cleared).
"""
import pytest
from django.core.management import call_command

from openoutreach.signals.email_hygiene import clean_junk_emails, is_junk_email
from openoutreach.signals.models import FloridaOrg, SalesLead

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("email,junk", [
    ("user@domain.com", True),
    ("info@anansiatlas.com", True),
    ("605a7baede@sentry-next.wixpress.com", True),
    ("john.doe@mail.de", True),
    ("info@realnonprofit.org", False),
    ("llewis@habitatocala.org", False),
    ("", False),
])
def test_is_junk_email(email, junk):
    assert is_junk_email(email) is junk


def test_clean_junk_emails_blanks_only_junk():
    FloridaOrg.objects.create(record_id="r1", ein="111111111", name="Good Org",
                              contact_email="info@goodorg.org")
    FloridaOrg.objects.create(record_id="r2", ein="222222222", name="Junk Org",
                              contact_email="user@domain.com")
    cleaned = clean_junk_emails(FloridaOrg.objects.all())
    assert cleaned == 1
    assert FloridaOrg.objects.get(ein="111111111").contact_email == "info@goodorg.org"
    assert FloridaOrg.objects.get(ein="222222222").contact_email == ""


def test_seed_cold_batch_splits_email_vs_phone_keepers():
    # One real EIN from each list.
    FloridaOrg.objects.create(record_id="e1", ein="592119445", name="Arnette House Inc",
                              city="Ocala", county="Marion", phone="(352) 622-4432",
                              contact_email="info@arnettehouse.org")
    FloridaOrg.objects.create(record_id="k1", ein="592349840", name="Interfaith Emergency Services Inc",
                              city="Ocala", county="Marion", phone="(352) 629-8868",
                              contact_email="605a7baede@sentry-next.wixpress.com")  # junk

    call_command("seed_cold_batch")

    emailable = SalesLead.objects.get(organization="Arnette House Inc")
    assert emailable.list_segment == "cold_florida_crm"
    assert emailable.email == "info@arnettehouse.org"      # → shows in cockpit

    keeper = SalesLead.objects.get(organization="Interfaith Emergency Services Inc")
    assert keeper.list_segment == "cold_call_list"         # its own Call List pipeline
    assert keeper.email == ""                               # junk cleaned → no email
    assert keeper.phone == "(352) 629-8868"                # still reachable by phone
    # Personalized call script is on the lead (shows in the pipeline card).
    assert "CALL SCRIPT" in keeper.outreach_draft
    assert "VOICEMAIL" in keeper.outreach_draft
    assert "Interfaith Emergency Services Inc" in keeper.outreach_draft

    # Idempotent — a second run promotes nothing new.
    before = SalesLead.objects.count()
    call_command("seed_cold_batch")
    assert SalesLead.objects.count() == before


def test_batch_cockpit_shows_emailable_not_keepers():
    from openoutreach.signals.outreach import outreach_queue
    FloridaOrg.objects.create(record_id="e1", ein="592119445", name="Arnette House Inc",
                              city="Ocala", county="Marion", contact_email="info@arnettehouse.org")
    FloridaOrg.objects.create(record_id="k1", ein="590946642", name="United Way Of Marion Co Inc",
                              city="Ocala", county="Marion", phone="(352) 732-9696")  # no email
    call_command("seed_cold_batch")
    queue_orgs = {l.organization for l in outreach_queue()}
    assert "Arnette House Inc" in queue_orgs
    assert "United Way Of Marion Co Inc" not in queue_orgs
