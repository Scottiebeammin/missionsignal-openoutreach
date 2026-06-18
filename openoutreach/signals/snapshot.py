from dataclasses import dataclass


@dataclass(frozen=True)
class OpportunityWebSnapshot:
    mission_overview: str
    readiness_score: int
    readiness_level: str
    opportunity_web_summary: list[tuple[str, str | int]]
    top_funder_pathways: list[str]
    top_partner_pathways: list[str]
    top_resource_gaps: list[str]
    top_opportunities: list[object]
    top_risks_gaps: list[str]
    recommended_next_actions: list[str]


def _dedupe(values: list[str], limit: int = 5) -> list[str]:
    seen = set()
    unique = []
    for value in values:
        clean = str(value or "").strip()
        key = clean.casefold()
        if clean and key not in seen:
            seen.add(key)
            unique.append(clean)
        if len(unique) >= limit:
            break
    return unique


def build_opportunity_web_snapshot(
    project,
    web,
    readiness,
    funding_readiness,
    partnership_readiness,
    discovery,
    document_evidence_health,
    match_overview,
) -> OpportunityWebSnapshot:
    organization = project.organization
    mission_overview = organization.organization_summary or organization.mission
    top_resource_gaps = _dedupe(
        document_evidence_health.document_summary.missing_critical_documents
        + document_evidence_health.evidence_summary.missing_evidence_items,
    )
    top_risks_gaps = _dedupe(
        web.opportunity_gaps
        + readiness.gaps
        + [gap.label for gap in match_overview.top_gaps],
    )
    actions = _dedupe(
        web.highest_leverage_actions
        + readiness.recommended_actions
        + match_overview.highest_leverage_actions,
        5,
    )
    return OpportunityWebSnapshot(
        mission_overview=mission_overview,
        readiness_score=readiness.overall_score,
        readiness_level=readiness.level,
        opportunity_web_summary=[
            ("Relationship Health", web.relationship_health_score),
            ("Active Opportunities", web.active_opportunities),
            ("Weighted Forecast", f"${web.forecast_value:,.0f}"),
            ("Opportunity Gaps", len(web.opportunity_gaps)),
        ],
        top_funder_pathways=[item.name for item in funding_readiness.recommended_funder_types[:5]],
        top_partner_pathways=[item.name for item in partnership_readiness.recommendations[:5]],
        top_resource_gaps=top_resource_gaps or ["No major document or evidence gaps detected."],
        top_opportunities=discovery.top_opportunities[:5],
        top_risks_gaps=top_risks_gaps or ["No major risks or gaps detected."],
        recommended_next_actions=actions or ["Use the Opportunity Web to prioritize the next action sprint."],
    )
