from dataclasses import dataclass

from openoutreach.funding.models import Opportunity
from openoutreach.signals.documents import build_document_evidence_health
from openoutreach.signals.forecasting import build_pipeline_forecast
from openoutreach.signals.relationships import build_relationship_overview
from openoutreach.signals.models import OrganizationContact, PartnerOrganization


@dataclass(frozen=True)
class WebNode:
    label: str
    status: str
    metrics: list[tuple[str, str | int]]
    highlights: list[str]
    gaps: list[str]


@dataclass(frozen=True)
class OpportunityWebOverview:
    nodes: list[WebNode]
    opportunity_gaps: list[str]
    highest_leverage_actions: list[str]
    relationship_health_score: int
    active_opportunities: int
    forecast_value: object
    ecosystem_health: int
    ecosystem_health_level: str
    strongest_asset: str
    biggest_constraint: str
    highest_leverage_relationship: str
    highest_leverage_opportunity: str
    opportunity_insight: str
    relationship_insight: str
    readiness_insight: str
    ecosystem_insight: str
    strategic_moves: list[str]


def _has_text(value) -> bool:
    return bool(str(value or "").strip())


def _has_values(values) -> bool:
    if isinstance(values, str):
        return _has_text(values)
    return any(_has_text(value) for value in values or [])


def _dedupe(values: list[str], limit: int = 6) -> list[str]:
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


def _geography(organization) -> str:
    parts = [organization.city, organization.county, organization.state]
    explicit = ", ".join(part for part in parts if _has_text(part))
    if explicit:
        return explicit
    if _has_values(organization.service_geographies):
        return ", ".join(organization.service_geographies[:3])
    return organization.service_area_notes or "Geography not defined"


def _type_counts(items, choices, attr_name: str) -> list[str]:
    rows = []
    for value, label in choices:
        count = sum(1 for item in items if getattr(item, attr_name) == value)
        if count:
            rows.append(f"{label}: {count}")
    return rows


def _funder_node(project, relationships) -> WebNode:
    contacts = list(project.organization_contacts.filter(status=OrganizationContact.Status.ACTIVE))
    funder_contacts = [
        contact
        for contact in contacts
        if contact.contact_type in {
            OrganizationContact.ContactType.FUNDER,
            OrganizationContact.ContactType.PROGRAM_OFFICER,
        }
    ]
    funding_partners = [
        partner
        for partner in project.relationship_partners.filter(status=PartnerOrganization.Status.ACTIVE)
        if partner.partner_type == PartnerOrganization.PartnerType.FUNDING_PARTNER
    ]
    gaps = []
    if not funder_contacts:
        gaps.append("Missing Program Officers")
    if not funding_partners:
        gaps.append("Missing Funding Partners")
    gaps.extend(gap for gap in relationships.relationship_gaps if "Funder" in gap or "program officer" in gap)
    return WebNode(
        label="Funders",
        status=relationships.health.level,
        metrics=[
            ("Funder contacts", len(funder_contacts)),
            ("Funding partners", len(funding_partners)),
            ("Relationship health", relationships.health.score),
        ],
        highlights=[f"{contact.name} - {contact.organization}" for contact in funder_contacts[:3]]
        + [partner.organization_name for partner in funding_partners[:2]]
        or ["No funder relationships documented yet."],
        gaps=_dedupe(gaps) or ["No major funder relationship gaps detected."],
    )


def _partner_node(project, relationships) -> WebNode:
    partners = list(project.relationship_partners.filter(status=PartnerOrganization.Status.ACTIVE))
    partner_types = {partner.partner_type for partner in partners}
    strong = [
        partner.organization_name
        for partner in partners
        if partner.relationship_strength == PartnerOrganization.RelationshipStrength.STRONG
    ]
    expected = {
        PartnerOrganization.PartnerType.COMMUNITY_PARTNER: "Community Partner",
        PartnerOrganization.PartnerType.GOVERNMENT_PARTNER: "Government Partner",
        PartnerOrganization.PartnerType.ACADEMIC_PARTNER: "Academic Partner",
        PartnerOrganization.PartnerType.CORPORATE_PARTNER: "Corporate Partner",
    }
    missing = [label for value, label in expected.items() if value not in partner_types]
    return WebNode(
        label="Partners",
        status="Diverse" if len(partner_types) >= 4 else "Needs Coverage",
        metrics=[
            ("Partner organizations", relationships.total_partners),
            ("Partner types", len(partner_types)),
            ("Strong partnerships", len(strong)),
        ],
        highlights=strong[:4] or [partner.organization_name for partner in partners[:4]] or ["No partners documented yet."],
        gaps=[f"Missing {label}" for label in missing] or ["No major partner category gaps detected."],
    )


def _contact_node(project, relationships) -> WebNode:
    contacts = list(project.organization_contacts.filter(status=OrganizationContact.Status.ACTIVE))
    return WebNode(
        label="Contacts",
        status=relationships.health.level,
        metrics=[
            ("Contact count", relationships.total_contacts),
            ("Strong relationships", relationships.strong_relationships),
            ("Developing relationships", relationships.developing_relationships),
        ],
        highlights=_type_counts(contacts, OrganizationContact.ContactType.choices, "contact_type")[:5]
        or ["No contact types documented yet."],
        gaps=relationships.relationship_gaps or ["No relationship gaps detected."],
    )


def _resource_node(project) -> WebNode:
    health = build_document_evidence_health(project)
    document_summary = health.document_summary
    evidence_summary = health.evidence_summary
    gaps = (
        [f"Missing document: {item}" for item in document_summary.missing_critical_documents]
        + [f"Missing evidence: {item}" for item in evidence_summary.missing_evidence_items]
    )
    readiness_assets = document_summary.available_documents + evidence_summary.total_evidence_items
    return WebNode(
        label="Resources",
        status="Ready" if readiness_assets and not gaps else "Needs Assets",
        metrics=[
            ("Documents", document_summary.total_documents),
            ("Evidence items", evidence_summary.total_evidence_items),
            ("Readiness assets", readiness_assets),
            ("Resource health", round((document_summary.readiness_score + evidence_summary.readiness_score) / 2)),
        ],
        highlights=[
            f"{document_summary.available_documents} reusable documents",
            f"{evidence_summary.outcome_evidence} outcome evidence items",
            f"{evidence_summary.impact_stories} impact stories",
        ],
        gaps=_dedupe(gaps) or ["No major resource readiness gaps detected."],
    )


def _opportunity_node(discovery_overview, forecast) -> WebNode:
    return WebNode(
        label="Opportunities",
        status=discovery_overview.best_opportunity_category,
        metrics=[
            ("Active opportunities", discovery_overview.active_opportunities),
            ("Forecast value", f"${forecast.weighted_forecast_value:,.0f}"),
            ("Awarded opportunities", discovery_overview.won_opportunities),
            ("Submitted opportunities", discovery_overview.applied_opportunities),
        ],
        highlights=[
            f"{item.opportunity.name} - Score {item.match.score}"
            for item in discovery_overview.top_opportunities[:4]
        ] or ["No opportunities available yet."],
        gaps=["No active opportunities in the inventory."] if not discovery_overview.active_opportunities else [],
    )


def _mission_node(project) -> WebNode:
    organization = project.organization
    gaps = []
    if not _has_text(organization.mission):
        gaps.append("Missing mission statement")
    if not _has_values(organization.focus_areas):
        gaps.append("Missing focus areas")
    if not _has_values(organization.beneficiaries):
        gaps.append("Missing beneficiaries")
    if _geography(organization) == "Geography not defined":
        gaps.append("Missing geography")
    return WebNode(
        label="Mission",
        status="Defined" if not gaps else "Needs Profile Detail",
        metrics=[
            ("Mission statement", "Present" if _has_text(organization.mission) else "Missing"),
            ("Focus areas", len(organization.focus_areas or [])),
            ("Beneficiaries", len(organization.beneficiaries or [])),
            ("Geography", _geography(organization)),
        ],
        highlights=[
            organization.mission or "Mission statement not defined.",
            ", ".join(organization.focus_areas[:4]) if organization.focus_areas else "No focus areas yet.",
            ", ".join(organization.beneficiaries[:4]) if organization.beneficiaries else "No beneficiaries yet.",
        ],
        gaps=gaps or ["No major mission profile gaps detected."],
    )


def _outcomes_node(project) -> WebNode:
    organization = project.organization
    health = build_document_evidence_health(project)
    outcomes = list(organization.outcomes_and_impact or [])
    gaps = []
    if not outcomes:
        gaps.append("Missing Outcomes")
    if health.evidence_summary.outcome_evidence == 0:
        gaps.append("Missing Evidence")
    return WebNode(
        label="Outcomes",
        status="Evidence-backed" if outcomes and health.evidence_summary.outcome_evidence else "Needs Evidence",
        metrics=[
            ("Outcomes tracked", len(outcomes)),
            ("Impact indicators", len(outcomes)),
            ("Evidence indicators", health.evidence_summary.outcome_evidence),
        ],
        highlights=outcomes[:4] or ["No outcomes documented yet."],
        gaps=gaps or ["No major outcome evidence gaps detected."],
    )


def _health_level(score: int) -> str:
    if score >= 85:
        return "Advanced"
    if score >= 70:
        return "Competitive"
    if score >= 50:
        return "Developing"
    return "Emerging"


def _first_specific_highlight(nodes: list[WebNode]) -> str:
    for node in nodes:
        for highlight in node.highlights:
            if highlight and not highlight.startswith("No ") and "not defined" not in highlight:
                return highlight
    return "Mission clarity"


def _highest_leverage_opportunity(discovery_overview) -> str:
    if discovery_overview.top_opportunities:
        item = discovery_overview.top_opportunities[0]
        return f"{item.opportunity.name} - match score {item.match.score}"
    return "No priority pathway selected yet"


def _opportunity_insight(discovery_overview) -> str:
    if discovery_overview.top_opportunities:
        item = discovery_overview.top_opportunities[0]
        return f"Pay attention to {item.opportunity.name}; it is the clearest current pathway in the inventory."
    return "Pay attention to Discovery; the web needs active opportunities before it can guide pursuit decisions."


def _readiness_insight(project) -> str:
    health = build_document_evidence_health(project)
    missing_documents = health.document_summary.missing_critical_documents
    missing_evidence = health.evidence_summary.missing_evidence_items
    if missing_documents:
        return f"Pay attention to document readiness; {missing_documents[0]} is still missing."
    if missing_evidence:
        return f"Pay attention to evidence readiness; {missing_evidence[0]} would strengthen future pursuits."
    return "Pay attention to keeping documents and evidence current as opportunities move into pursuit."


def _strategic_moves(relationships, discovery_overview, opportunity_gaps: list[str], project) -> list[str]:
    moves = []
    if relationships.key_contacts:
        contact = relationships.key_contacts[0]
        moves.append(f"Strengthen relationship with {contact.name} at {contact.organization}.")
    elif relationships.key_partners:
        partner = relationships.key_partners[0]
        moves.append(f"Formalize partnership with {partner.organization_name}.")
    if discovery_overview.top_opportunities:
        moves.append(f"Pursue {discovery_overview.top_opportunities[0].opportunity.name}.")
    health = build_document_evidence_health(project)
    if health.document_summary.missing_critical_documents:
        moves.append(f"Improve readiness documentation: {health.document_summary.missing_critical_documents[0]}.")
    elif health.evidence_summary.missing_evidence_items:
        moves.append(f"Add evidence: {health.evidence_summary.missing_evidence_items[0]}.")
    if opportunity_gaps and len(moves) < 3:
        moves.append(f"Close web gap: {opportunity_gaps[0]}.")
    return _dedupe(moves, 3)


def build_opportunity_web(project, discovery_overview) -> OpportunityWebOverview:
    relationships = build_relationship_overview(project)
    forecast = build_pipeline_forecast(project)
    nodes = [
        _mission_node(project),
        _funder_node(project, relationships),
        _partner_node(project, relationships),
        _contact_node(project, relationships),
        _resource_node(project),
        _opportunity_node(discovery_overview, forecast),
        _outcomes_node(project),
    ]
    gap_candidates = []
    for node in nodes:
        gap_candidates.extend(node.gaps)
    opportunity_gaps = _dedupe(
        [
            gap
            for gap in gap_candidates
            if gap and not gap.startswith("No major")
        ],
        8,
    )
    if not opportunity_gaps:
        opportunity_gaps = ["No major opportunity web gaps detected."]

    action_map = {
        "Missing Government Relationships": "Add city, county, school, library, or workforce contacts to strengthen public-sector pathways.",
        "Missing Funding Partners": "Identify funding partners and program officers tied to priority opportunities.",
        "Missing Program Officers": "Add program officer contacts for active grant and foundation lanes.",
        "Missing Evidence": "Add outcome evidence and impact proof to strengthen readiness.",
        "Missing Readiness Components": "Complete readiness assets in the Document Vault and Evidence Library.",
    }
    actions = []
    gap_text = " ".join(opportunity_gaps).casefold()
    if "government" in gap_text:
        actions.append(action_map["Missing Government Relationships"])
    if "funding" in gap_text or "program officer" in gap_text:
        actions.append(action_map["Missing Funding Partners"])
    if "evidence" in gap_text or "document" in gap_text:
        actions.append(action_map["Missing Evidence"])
    actions.extend([
        relationships.health.highest_leverage_action,
        "Use the Opportunity Web to connect priority opportunities to contacts, partners, resources, and outcomes.",
    ])
    ecosystem_health = round(
        (
            relationships.health.score
            + nodes[4].metrics[3][1]
            + min(discovery_overview.active_opportunities * 10, 100)
        )
        / 3
    )
    strongest_asset = _first_specific_highlight(nodes)
    biggest_constraint = opportunity_gaps[0] if opportunity_gaps else "No major constraint detected"
    highest_leverage_opportunity = _highest_leverage_opportunity(discovery_overview)
    relationship_insight = relationships.health.highest_leverage_action
    readiness_insight = _readiness_insight(project)
    opportunity_insight = _opportunity_insight(discovery_overview)
    ecosystem_insight = (
        "The web is strongest when priority opportunities are connected to named relationships, reusable resources, and outcome proof."
    )
    return OpportunityWebOverview(
        nodes=nodes,
        opportunity_gaps=opportunity_gaps,
        highest_leverage_actions=_dedupe(actions, 3),
        relationship_health_score=relationships.health.score,
        active_opportunities=discovery_overview.active_opportunities,
        forecast_value=forecast.weighted_forecast_value,
        ecosystem_health=ecosystem_health,
        ecosystem_health_level=_health_level(ecosystem_health),
        strongest_asset=strongest_asset,
        biggest_constraint=biggest_constraint,
        highest_leverage_relationship=relationships.health.highest_leverage_action,
        highest_leverage_opportunity=highest_leverage_opportunity,
        opportunity_insight=opportunity_insight,
        relationship_insight=relationship_insight,
        readiness_insight=readiness_insight,
        ecosystem_insight=ecosystem_insight,
        strategic_moves=_strategic_moves(relationships, discovery_overview, opportunity_gaps, project),
    )
