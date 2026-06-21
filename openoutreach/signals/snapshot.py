from dataclasses import dataclass


@dataclass(frozen=True)
class SnapshotInsight:
    label: str
    rationale: str
    factors: list[str]


@dataclass(frozen=True)
class SnapshotOpportunityInsight:
    name: str
    score: int
    level: str
    opportunity_type: str
    priority: str
    rationale: str
    factors: list[str]


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
    top_funder_pathway_insights: list[SnapshotInsight]
    top_partner_pathway_insights: list[SnapshotInsight]
    relationship_target_insights: list[SnapshotInsight]
    top_opportunity_insights: list[SnapshotOpportunityInsight]
    recommended_action_insights: list[SnapshotInsight]


SECTOR_INTELLIGENCE = {
    "youth": {
        "label": "Youth Development",
        "terms": ["youth", "student", "students", "school", "afterschool", "teen", "young adult"],
        "funder_pathways": [
            "Youth Development Funders",
            "Youth Services Agencies",
            "Afterschool Networks",
            "School District Partnership Funds",
        ],
        "partner_pathways": [
            "School District Partnerships",
            "Afterschool Networks",
            "Youth Services Agencies",
            "Mentoring Organizations",
        ],
        "relationship_targets": [
            "School District Partnership",
            "Youth Services Agency",
            "Afterschool Network",
            "Community Foundation Youth Program Officer",
        ],
        "brief_focus": "youth outcomes, referral pathways, and program evidence",
    },
    "workforce": {
        "label": "Workforce Development",
        "terms": [
            "workforce", "job", "jobs", "career", "employment", "training", "credential",
            "skills", "employer", "placement",
        ],
        "funder_pathways": [
            "Workforce Boards",
            "Skills Training Funders",
            "Employer Coalition Funds",
            "Career Pathway Grantmakers",
        ],
        "partner_pathways": [
            "Workforce Boards",
            "Employer Coalitions",
            "Chamber Partnerships",
            "Community College Training Partners",
        ],
        "relationship_targets": [
            "County Workforce Board",
            "Employer Coalition",
            "Chamber Workforce Committee",
            "Community College Training Dean",
        ],
        "brief_focus": "job outcomes, employer demand, credentials, and placement evidence",
    },
    "health": {
        "label": "Community Health",
        "terms": ["health", "healthcare", "clinic", "hospital", "wellness", "mental health", "public health"],
        "funder_pathways": [
            "Health Foundations",
            "Hospital Community Benefit Funds",
            "Public Health Agencies",
            "Mental Health Grantmakers",
        ],
        "partner_pathways": [
            "Hospital Systems",
            "Public Health Agencies",
            "Community Clinics",
            "Mental Health Provider Networks",
        ],
        "relationship_targets": [
            "Local Public Health Department",
            "Hospital Community Benefit Team",
            "Community Clinic Partner",
            "Mental Health Provider Network",
        ],
        "brief_focus": "health outcomes, referral partners, and community benefit alignment",
    },
    "food": {
        "label": "Food Security",
        "terms": ["food", "hunger", "pantry", "meal", "meals", "nutrition", "agriculture", "grocery"],
        "funder_pathways": [
            "Hunger Relief Funders",
            "Food Access Grants",
            "Agricultural Partnerships",
            "Community Nutrition Funders",
        ],
        "partner_pathways": [
            "Food Banks",
            "Hunger Relief Networks",
            "Agricultural Partnerships",
            "Senior Nutrition Partners",
        ],
        "relationship_targets": [
            "Regional Food Bank",
            "County Food Access Office",
            "Local Grower Network",
            "Senior Center Partner",
        ],
        "brief_focus": "food access outcomes, distribution partners, and community need evidence",
    },
    "environment": {
        "label": "Environmental Stewardship",
        "terms": [
            "environment", "environmental", "climate", "river", "watershed",
            "conservation", "sustainability", "green", "stewardship",
        ],
        "funder_pathways": [
            "Conservation Funders",
            "Watershed Programs",
            "Environmental Justice Grants",
            "Sustainability Partnerships",
        ],
        "partner_pathways": [
            "Watershed Programs",
            "Conservation Organizations",
            "Parks Departments",
            "School Sustainability Partners",
        ],
        "relationship_targets": [
            "Watershed Program",
            "County Parks Department",
            "Conservation Funder",
            "School Sustainability Coordinator",
        ],
        "brief_focus": "place-based outcomes, stewardship partners, and environmental evidence",
    },
}


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


def _context_text(project) -> str:
    organization = project.organization
    values = [
        organization.name,
        organization.mission,
        organization.organization_summary,
        project.programs,
        organization.organization_type,
        organization.budget_range,
        organization.city,
        organization.county,
        organization.state,
        *organization.focus_areas,
        *organization.beneficiaries,
        *organization.service_geographies,
        *organization.outcomes_and_impact,
        *organization.existing_partnerships,
    ]
    return "\n".join(str(value or "") for value in values).casefold()


def _sector_profile(project) -> dict:
    text = _context_text(project)
    scored = []
    for key, profile in SECTOR_INTELLIGENCE.items():
        score = sum(1 for term in profile["terms"] if term in text)
        scored.append((score, key, profile))
    scored.sort(key=lambda item: (-item[0], item[1]))
    if scored and scored[0][0] > 0:
        return scored[0][2]
    return {
        "label": "Community Development",
        "funder_pathways": [
            "Community Development Funders",
            "Local Government Grants",
            "Community Foundations",
            "Corporate Civic Impact Funds",
        ],
        "partner_pathways": [
            "Community-Based Organizations",
            "Local Government Agencies",
            "Community Foundations",
            "Anchor Institution Partners",
        ],
        "relationship_targets": [
            "Community Foundation Program Officer",
            "City Community Development Office",
            "Anchor Institution Partnership Lead",
            "Neighborhood Coalition",
        ],
        "brief_focus": "mission fit, local need, partner roles, and community outcomes",
    }


def _organization_context(project) -> dict:
    organization = project.organization
    geography = _dedupe(
        [
            organization.city,
            organization.county,
            organization.state,
            *organization.service_geographies,
        ],
        4,
    )
    return {
        "focus": _dedupe(organization.focus_areas, 4),
        "beneficiaries": _dedupe(organization.beneficiaries, 4),
        "geography": geography,
        "programs_defined": bool(str(project.programs or "").strip()),
        "outcomes_defined": bool(organization.outcomes_and_impact),
        "partnerships_defined": bool(organization.existing_partnerships),
        "funding_defined": bool(organization.current_funding_sources),
        "budget_defined": bool(str(organization.budget_range or "").strip()),
    }


def _pathway_rationale(pathway: str, sector: dict, context: dict) -> SnapshotInsight:
    factors = ["Mission Alignment"]
    rationale_parts = [f"{sector['label']} appears in the mission, programs, or target population."]
    if context["beneficiaries"]:
        factors.append("Beneficiary Alignment")
        rationale_parts.append(f"Serves {context['beneficiaries'][0]}.")
    if context["geography"]:
        factors.append("Geographic Alignment")
        rationale_parts.append(f"Can be targeted around {context['geography'][0]}.")
    if context["programs_defined"]:
        factors.append("Program Alignment")
    return SnapshotInsight(pathway, " ".join(rationale_parts), factors[:4])


def _pathway_insights(pathways: list[str], sector: dict, context: dict, limit: int = 5) -> list[SnapshotInsight]:
    return [
        _pathway_rationale(pathway, sector, context)
        for pathway in _dedupe(pathways, limit)
    ]


def _relationship_target_insights(sector: dict, context: dict) -> list[SnapshotInsight]:
    insights = []
    geography = context["geography"][0] if context["geography"] else "the service area"
    for target in sector["relationship_targets"][:4]:
        factors = ["Relationship Alignment", "Mission Alignment"]
        if context["geography"]:
            factors.append("Geographic Alignment")
        rationale = (
            f"Use this target archetype to turn {sector['label']} strategy into a named outreach list "
            f"for {geography}."
        )
        insights.append(SnapshotInsight(f"Pursue {target}", rationale, factors))
    return insights


def _factor_summary(factors: list[str], fallback: list[str]) -> list[str]:
    clean = _dedupe(factors, 4)
    return clean or fallback[:3]


def _opportunity_insights(discovery) -> list[SnapshotOpportunityInsight]:
    insights = []
    for item in discovery.top_opportunities[:5]:
        match = item.match
        factors = _factor_summary(match.match_factors, ["Mission Alignment"])
        reasons = _dedupe(match.reasons, 3)
        if reasons:
            rationale = "Matches because of " + ", ".join(reasons).rstrip(".") + "."
        else:
            rationale = "Matches the mission profile and current opportunity inventory."
        insights.append(
            SnapshotOpportunityInsight(
                name=item.opportunity.name,
                score=match.score,
                level=match.level,
                opportunity_type=item.opportunity.get_opportunity_type_display(),
                priority=item.opportunity.get_priority_level_display(),
                rationale=rationale,
                factors=factors,
            )
        )
    return insights


def _action_insights(
    sector: dict,
    context: dict,
    top_opportunity_insights: list[SnapshotOpportunityInsight],
    relationship_targets: list[SnapshotInsight],
    top_resource_gaps: list[str],
    top_risks_gaps: list[str],
    fallback_actions: list[str],
) -> list[SnapshotInsight]:
    actions = []
    if top_opportunity_insights:
        opportunity = top_opportunity_insights[0]
        actions.append(
            SnapshotInsight(
                f"Validate fit for {opportunity.name}.",
                f"Highest-ranked pathway with {opportunity.level.lower()} and visible alignment signals.",
                _factor_summary(opportunity.factors, ["Opportunity Alignment"]),
            )
        )
    if relationship_targets:
        target = relationship_targets[0]
        actions.append(
            SnapshotInsight(
                target.label + ".",
                target.rationale,
                target.factors,
            )
        )
    if top_resource_gaps and "No major" not in top_resource_gaps[0]:
        actions.append(
            SnapshotInsight(
                f"Close the {top_resource_gaps[0].lower()} gap.",
                "This improves the credibility of the Snapshot and future pursuit package.",
                ["Readiness Alignment", "Evidence Alignment"],
            )
        )
    if not context["outcomes_defined"]:
        actions.append(
            SnapshotInsight(
                f"Add measurable {sector['label'].lower()} outcomes.",
                f"Outcomes make {sector['brief_focus']} easier for funders and partners to trust.",
                ["Readiness Alignment", "Strategic Value"],
            )
        )
    elif top_risks_gaps and "No major" not in top_risks_gaps[0]:
        actions.append(
            SnapshotInsight(
                f"Resolve: {top_risks_gaps[0]}.",
                "This is one of the highest-frequency constraints across the current web.",
                ["Readiness Alignment", "Risk Reduction"],
            )
        )
    actions.append(
        SnapshotInsight(
            f"Create a one-page {sector['label']} opportunity brief.",
            f"Focus the brief on {sector['brief_focus']} so outreach feels specific, not generic.",
            ["Mission Alignment", "Program Alignment", "Relationship Alignment"],
        )
    )
    for action in fallback_actions:
        actions.append(
            SnapshotInsight(
                action,
                "Included because it appears in the current Opportunity Web, readiness, or matching analysis.",
                ["Snapshot Alignment"],
            )
        )
    unique = []
    seen = set()
    for action in actions:
        key = action.label.casefold()
        if key not in seen:
            seen.add(key)
            unique.append(action)
        if len(unique) >= 5:
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
    sector = _sector_profile(project)
    context = _organization_context(project)
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
    funder_pathway_insights = _pathway_insights(
        sector["funder_pathways"] + [item.name for item in funding_readiness.recommended_funder_types],
        sector,
        context,
    )
    partner_pathway_insights = _pathway_insights(
        sector["partner_pathways"] + [item.name for item in partnership_readiness.recommendations],
        sector,
        context,
    )
    relationship_target_insights = _relationship_target_insights(sector, context)
    top_opportunity_insights = _opportunity_insights(discovery)
    recommended_action_insights = _action_insights(
        sector,
        context,
        top_opportunity_insights,
        relationship_target_insights,
        top_resource_gaps,
        top_risks_gaps,
        actions,
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
        top_funder_pathways=[item.label for item in funder_pathway_insights],
        top_partner_pathways=[item.label for item in partner_pathway_insights],
        top_resource_gaps=top_resource_gaps or ["No major document or evidence gaps detected."],
        top_opportunities=discovery.top_opportunities[:5],
        top_risks_gaps=top_risks_gaps or ["No major risks or gaps detected."],
        recommended_next_actions=[
            item.label for item in recommended_action_insights
        ] or ["Use the Opportunity Web to prioritize the next action sprint."],
        top_funder_pathway_insights=funder_pathway_insights,
        top_partner_pathway_insights=partner_pathway_insights,
        relationship_target_insights=relationship_target_insights,
        top_opportunity_insights=top_opportunity_insights,
        recommended_action_insights=recommended_action_insights,
    )
