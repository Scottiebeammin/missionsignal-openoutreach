from django.db import transaction

from openoutreach.funding.identity import (
    build_identity_key,
    canonical_url_identity,
    composite_identity,
    normalize_canonical_url,
)
from openoutreach.funding.models import FundingOpportunity, FundingOpportunitySource


@transaction.atomic
def resolve_funding_opportunity(
    *,
    source_record,
    title,
    funder=None,
    canonical_url="",
    deadline_at=None,
    opportunity_type="",
    defaults=None,
):
    """Resolve or create one normalized opportunity and link its source evidence."""
    existing_link = FundingOpportunitySource.objects.select_related("opportunity").filter(
        source_record=source_record,
    ).first()
    if existing_link:
        return existing_link.opportunity, False

    normalized_url = normalize_canonical_url(canonical_url or source_record.canonical_url)
    funder_name = funder.name if funder else ""
    identity_key = build_identity_key(
        source_key=source_record.source.key,
        external_id=source_record.external_id,
        canonical_url=normalized_url,
        funder_name=funder_name,
        title=title,
        deadline=deadline_at,
        opportunity_type=opportunity_type,
    )

    opportunity = None
    if normalized_url:
        opportunity = FundingOpportunity.objects.filter(
            identity_key=canonical_url_identity(normalized_url),
        ).first()
    if opportunity is None:
        opportunity = FundingOpportunity.objects.filter(
            identity_key=composite_identity(
                funder_name=funder_name,
                title=title,
                deadline=deadline_at,
                opportunity_type=opportunity_type,
            ),
        ).first()
    if opportunity is None:
        values = {
            "title": title,
            "funder": funder,
            "canonical_url": normalized_url,
            "deadline_at": deadline_at,
            "opportunity_type": opportunity_type,
            **(defaults or {}),
        }
        opportunity, created = FundingOpportunity.objects.get_or_create(
            identity_key=identity_key,
            defaults=values,
        )
    else:
        created = False

    FundingOpportunitySource.objects.create(
        opportunity=opportunity,
        source_record=source_record,
        source_external_id=source_record.external_id,
        source_url=normalize_canonical_url(source_record.canonical_url),
    )
    return opportunity, created
