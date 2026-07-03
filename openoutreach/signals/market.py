"""Florida Market Database logic — promote universe orgs into the sales pipeline.

The FloridaOrg table is the founder's statewide prospect UNIVERSE (all 114k+
IRS exempt organizations in Florida). Rows here are not leads; an operator
promotes one into the pipeline explicitly, which creates a SalesLead in the
cold_florida_crm segment and back-links it via FloridaOrg.promoted_lead.
"""

from django.db import transaction

from openoutreach.signals.models import FloridaOrg, SalesLead


def _fmt_amount(value):
    return f"${value:,}" if value is not None else "unknown"


def build_provenance_notes(org: FloridaOrg) -> str:
    return (
        f"Promoted from Florida Market Database ({org.record_id}). "
        f"EIN: {org.ein or 'unknown'}. "
        f"NTEE: {org.ntee_code or 'unclassified'} ({org.ntee_sector or 'Unknown sector'}). "
        f"Assets: {_fmt_amount(org.asset_amount)}. Income: {_fmt_amount(org.income_amount)}. "
        f"Location: {org.city or 'unknown city'}, {org.county or 'unknown'} County."
    )


def promote_org_to_pipeline(org: FloridaOrg):
    """Create a cold_florida_crm SalesLead for this org, exactly once.

    Returns (lead, created). A second call is a no-op returning the existing
    lead — the promoted_lead FK is the idempotency guard.
    """
    with transaction.atomic():
        org = FloridaOrg.objects.select_for_update().get(pk=org.pk)
        if org.promoted_lead_id is not None:
            return org.promoted_lead, False
        lead = SalesLead.objects.create(
            name=org.name,
            organization=org.name,
            source=SalesLead.Source.COLD,
            status=SalesLead.Status.NEW,
            list_segment=SalesLead.Segment.COLD_FLORIDA_CRM,
            warmth=SalesLead.Warmth.COLD,
            region=org.county,
            notes=build_provenance_notes(org),
        )
        org.promoted_lead = lead
        org.save(update_fields=["promoted_lead", "updated_at"])
    return lead, True
