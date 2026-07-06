"""
Load the curated Ocala + Gainesville cold-outreach batch into the pipeline.

Cleans junk emails first, then promotes each org (by EIN) to a cold_florida_crm
SalesLead — idempotent (an already-promoted org is skipped). The 20 with a valid
email land in the Outreach Cockpit ready to send; the 6 strong "keepers" with a
phone/website but no email stay in the Pipeline for call/contact-form outreach.

    python manage.py seed_cold_batch

Curated with Marcus on 2026-07-05 (Ocala/Marion + Gainesville/Alachua nonprofits).
"""
from django.core.management.base import BaseCommand

from openoutreach.signals.email_hygiene import clean_junk_emails
from openoutreach.signals.market import promote_org_to_pipeline
from openoutreach.signals.models import FloridaOrg, SalesLead
from openoutreach.signals.outreach import compose_call_script

# 20 with a valid direct email → the Outreach Cockpit.
EMAILABLE_EINS = [
    "592992077",  # Habitat for Humanity Ocala
    "592119445",  # Arnette House
    "593575631",  # Marion Co. Children's Advocacy (Kimberly's Center)
    "300178066",  # Ambleside School of Ocala
    "208657795",  # Project Hope of Marion County
    "824751578",  # Zero Hour Life Center
    "591763307",  # Don Garlits Museum
    "274168619",  # Garden Worship Center
    "592017427",  # Education for Life / Women's Pregnancy Center
    "592850646",  # Harvest International
    "593563675",  # Kenny's Place of Marion County
    "600000676",  # Marion County Literacy Council
    "061724005",  # Night Runners Mobile Crisis Services
    "590618591",  # VFW Post 4209 (Marion)
    "591140179",  # The Arc of Alachua County
    "431960048",  # GRACE Marketplace (Alachua Coalition for the Homeless)
    "593118984",  # Healthy Start of North Central Florida
    "593665622",  # Early Learning Coalition of Alachua County
    "237098099",  # Florida Camp for Children & Youth with Diabetes
    "593553820",  # Alachua Learning Center
]

# Strong fits with a phone + website but no usable email → stay in the Pipeline
# for call / contact-form outreach (their junk email gets cleaned to empty first).
PHONE_KEEPER_EINS = [
    "592349840",  # Interfaith Emergency Services
    "237362750",  # Marion Senior Services
    "273644705",  # Wear Gloves
    "591172127",  # Boys & Girls Club of Marion County
    "590946642",  # United Way of Marion County
    "208941924",  # Sheltering Hands
]


class Command(BaseCommand):
    help = "Clean junk emails, then promote the curated Ocala+Gainesville cold batch to the pipeline."

    def handle(self, *args, **options):
        cleaned = clean_junk_emails(FloridaOrg.objects.all())
        self.stdout.write(f"Cleaned {cleaned:,} junk emails.")

        emailed = kept = missing = already = 0
        for ein, label in ((e, "email") for e in EMAILABLE_EINS):
            org = FloridaOrg.objects.filter(ein=ein).first()
            if not org:
                self.stdout.write(self.style.WARNING(f"  missing EIN {ein}"))
                missing += 1
                continue
            _lead, created = promote_org_to_pipeline(org)
            emailed += 1 if created else 0
            already += 0 if created else 1
        for ein in PHONE_KEEPER_EINS:
            org = FloridaOrg.objects.filter(ein=ein).first()
            if not org:
                self.stdout.write(self.style.WARNING(f"  missing EIN {ein}"))
                missing += 1
                continue
            lead, created = promote_org_to_pipeline(org, segment=SalesLead.Segment.COLD_CALL_LIST)
            # Drop the personalized call script onto the lead so it's right there
            # in the pipeline card when Marcus dials (refresh even if pre-promoted).
            lead.outreach_draft = compose_call_script(lead, contact_name=org.principal_officer)
            lead.save(update_fields=["outreach_draft", "updated_at"])
            kept += 1 if created else 0
            already += 0 if created else 1

        self.stdout.write(self.style.SUCCESS(
            f"Batch loaded: {emailed} emailable → cockpit, {kept} phone-keepers → Call List, "
            f"{already} already promoted, {missing} EINs not found."
        ))
