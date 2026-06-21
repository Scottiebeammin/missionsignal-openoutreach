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
    why_now: str
    preparation_required: str
    risks: str
    factors: list[str]
    source_indicators: list[str]


@dataclass(frozen=True)
class SnapshotFunderFit:
    archetype: str
    alignment_level: str
    rationale: str
    preparation_steps: list[str]
    source_indicators: list[str]


@dataclass(frozen=True)
class SnapshotSourceSummary:
    sources_reviewed: int
    funders_reviewed: int
    opportunities_reviewed: int
    ecosystem_entities_reviewed: int
    source_types_used: list[str]
    important_sources: list[str]
    missing_source_types: list[str]
    guidance: list[str]


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
    source_summary: SnapshotSourceSummary
    funder_fit_insights: list[SnapshotFunderFit]
    ecosystem_gap_insights: list[SnapshotInsight]
    readiness_context_insights: list[SnapshotInsight]


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


def _overlap_count(left: list[str], right: list[str]) -> int:
    left_text = " ".join(str(value or "") for value in left).casefold()
    return sum(1 for value in right if str(value or "").casefold() in left_text)


def _record_source_label(source_references: list) -> str:
    labels = []
    for source in source_references or []:
        if isinstance(source, dict):
            labels.append(source.get("title") or source.get("url") or source.get("source"))
        else:
            labels.append(str(source))
    labels = _dedupe(labels, 2)
    if not labels:
        return ""
    return " Source reference: " + "; ".join(labels) + "."


def _geography_overlap(record_geography: list[str], context: dict) -> bool:
    return _overlap_count(record_geography, context["geography"]) > 0


def _opportunity_source_indicators(item, context: dict) -> list[str]:
    opportunity = item.opportunity
    indicators = []
    if opportunity.source_references:
        indicators.append("Verified Opportunity")
    if opportunity.verification_status in {
        opportunity.VerificationStatus.REVIEWED,
        opportunity.VerificationStatus.VERIFIED,
    }:
        indicators.append("Reviewed Source")
    if _geography_overlap(opportunity.geography, context):
        indicators.append("Strong Geographic Fit")
    if item.match.score >= 85:
        indicators.append("High Alignment")
    if opportunity.source_organization:
        indicators.append("Named Source")
    if opportunity.funding_amount:
        indicators.append("Funding Amount Available")
    return _dedupe(indicators, 4)


def _funder_source_indicators(funder, score: int, context: dict) -> list[str]:
    indicators = ["Named Funder"]
    if funder.source_references:
        indicators.append("Source-backed Funder")
    if funder.verification_status in {
        funder.VerificationStatus.REVIEWED,
        funder.VerificationStatus.VERIFIED,
    }:
        indicators.append("Reviewed Source")
    if _geography_overlap(funder.geography, context):
        indicators.append("Strong Geographic Fit")
    if score >= 85:
        indicators.append("High Alignment")
    if funder.intelligence_status == funder.IntelligenceStatus.ACTIVE:
        indicators.append("Active Intelligence")
    return _dedupe(indicators, 4)


def _named_funder_fit_insights(sector: dict, context: dict) -> list[SnapshotFunderFit]:
    from openoutreach.funding.models import Funder

    sector_terms = sector.get("terms", []) + context["focus"] + context["beneficiaries"]
    candidates = []
    for funder in Funder.objects.filter(active=True).exclude(
        intelligence_status=Funder.IntelligenceStatus.ARCHIVED,
    ):
        score = 70
        score += min(_overlap_count(funder.focus_areas, sector_terms) * 6, 18)
        score += min(_overlap_count(funder.beneficiaries, context["beneficiaries"] + sector_terms) * 5, 12)
        score += min(_overlap_count(funder.geography, context["geography"]) * 5, 10)
        if funder.funder_type in {
            Funder.FunderType.COMMUNITY_FOUNDATION,
            Funder.FunderType.WORKFORCE_BOARD,
            Funder.FunderType.LOCAL_GOVERNMENT,
            Funder.FunderType.STATE_GOVERNMENT,
        }:
            score += 4
        candidates.append((min(score, 98), funder.name.casefold(), funder))
    candidates.sort(key=lambda item: (-item[0], item[1]))

    insights = []
    for score, _sort_name, funder in candidates[:5]:
        preparation = []
        if not context["outcomes_defined"]:
            preparation.append("Add outcome evidence tied to the target program.")
        if not context["budget_defined"]:
            preparation.append("Prepare a clear request budget and funding use.")
        if not context["funding_defined"]:
            preparation.append("Document current and recent funding sources.")
        preparation.append(f"Prepare outreach for {funder.get_funder_type_display()} review.")
        rationale = (
            f"{funder.name} is a named {funder.get_funder_type_display().lower()} with alignment around "
            f"{', '.join(_dedupe(funder.focus_areas, 2)) or sector['label'].lower()}."
        )
        if context["geography"] and funder.geography:
            rationale += f" Geography overlaps with {context['geography'][0]}."
        rationale += _record_source_label(funder.source_references)
        insights.append(
            SnapshotFunderFit(
                archetype=funder.name,
                alignment_level=_alignment_level(score),
                rationale=rationale,
                preparation_steps=_dedupe(preparation, 3),
                source_indicators=_funder_source_indicators(funder, score, context),
            )
        )
    return insights


def _named_relationship_insights(project, sector: dict, context: dict) -> list[SnapshotInsight]:
    from openoutreach.funding.models import PartnerOrganization as EcosystemPartner
    from openoutreach.signals.models import PartnerOrganization as RelationshipPartner

    sector_terms = sector.get("terms", []) + context["focus"] + context["beneficiaries"]
    candidates = []
    for partner in RelationshipPartner.objects.filter(
        project=project,
        status=RelationshipPartner.Status.ACTIVE,
    ):
        score = 75
        score += min(_overlap_count(partner.geography, context["geography"]) * 5, 10)
        text = " ".join([
            partner.partner_type,
            partner.notes,
            partner.mission_alignment_notes,
            partner.opportunity_notes,
            partner.relationship_notes,
        ]).casefold()
        score += min(sum(1 for term in sector_terms if str(term).casefold() in text) * 5, 15)
        candidates.append((min(score, 98), partner.organization_name.casefold(), partner, "relationship"))
    for partner in EcosystemPartner.objects.filter(active=True).exclude(
        intelligence_status=EcosystemPartner.IntelligenceStatus.ARCHIVED,
    ):
        score = 70
        score += min(_overlap_count(partner.focus_areas, sector_terms) * 5, 15)
        score += min(_overlap_count(partner.geography, context["geography"]) * 5, 10)
        candidates.append((min(score, 95), partner.name.casefold(), partner, "ecosystem"))
    candidates.sort(key=lambda item: (-item[0], item[1]))

    insights = []
    for _score, _sort_name, partner, source in candidates[:2]:
        factors = ["Relationship Alignment", "Mission Alignment"]
        if context["geography"]:
            factors.append("Geographic Alignment")
        if source == "relationship":
            label = f"Strengthen {partner.organization_name}"
            rationale = (
                partner.relationship_notes
                or partner.opportunity_notes
                or partner.mission_alignment_notes
                or partner.notes
                or f"This named partner can help turn {sector['label'].lower()} strategy into concrete outreach."
            )
            rationale += _record_source_label(partner.source_references)
        else:
            label = f"Pursue {partner.name}"
            rationale = (
                partner.relationship_notes
                or partner.opportunity_notes
                or partner.mission_alignment_notes
                or partner.notes
                or f"This ecosystem organization is aligned with {sector['label'].lower()} pathways."
            )
            rationale += _record_source_label(partner.source_references)
        insights.append(SnapshotInsight(label, rationale, factors[:4]))
    return insights


def _archetype_relationship_target_insights(sector: dict, context: dict) -> list[SnapshotInsight]:
    insights = []
    geography = context["geography"][0] if context["geography"] else "the service area"
    for target in sector["relationship_targets"][:4]:
        factors = ["Relationship Alignment", "Mission Alignment"]
        if context["geography"]:
            factors.append("Geographic Alignment")
        unlock = "funding conversations, partner referrals, and stronger opportunity credibility"
        if "Workforce" in target or "Employer" in target or "Chamber" in target:
            unlock = "workforce grants, employer-backed pathways, and placement credibility"
        elif "School" in target or "Youth" in target or "Afterschool" in target:
            unlock = "youth services funding, student referral channels, and school partnership evidence"
        elif "Health" in target or "Hospital" in target or "Clinic" in target:
            unlock = "public health partnerships, community benefit funding, and referral pathways"
        elif "Food" in target or "Grower" in target or "Senior Center" in target:
            unlock = "food access funding, distribution partnerships, and community need evidence"
        elif "Watershed" in target or "Parks" in target or "Conservation" in target:
            unlock = "conservation funding, place-based stewardship partnerships, and environmental proof"
        rationale = (
            f"Use this target archetype to turn {sector['label']} strategy into a named outreach list "
            f"for {geography}; it can unlock {unlock}."
        )
        insights.append(SnapshotInsight(f"Pursue {target}", rationale, factors))
    return insights


def _relationship_target_insights(project, sector: dict, context: dict) -> list[SnapshotInsight]:
    insights = _named_relationship_insights(project, sector, context)
    insights.extend(_archetype_relationship_target_insights(sector, context))
    unique = []
    seen = set()
    for insight in insights:
        key = insight.label.casefold()
        if key not in seen:
            seen.add(key)
            unique.append(insight)
        if len(unique) >= 4:
            break
    return unique


def _factor_summary(factors: list[str], fallback: list[str]) -> list[str]:
    clean = _dedupe(factors, 4)
    return clean or fallback[:3]


def _opportunity_timing(item) -> str:
    opportunity = item.opportunity
    if getattr(opportunity, "deadline", None):
        return f"Deadline is visible for {opportunity.deadline:%b %-d, %Y}, so fit should be confirmed before preparation time is lost."
    if opportunity.priority_level == opportunity.PriorityLevel.HIGH:
        return "It is marked high priority, so it should be reviewed before lower-value inventory."
    if opportunity.status in {opportunity.Status.ACTIVE, opportunity.Status.UPCOMING}:
        return f"It is currently {opportunity.get_status_display().lower()}, making it timely enough for near-term screening."
    return "It remains useful as a monitored pathway, but timing should be confirmed before pursuit."


def _opportunity_preparation(match, context: dict) -> str:
    if match.improvement_suggestions:
        return match.improvement_suggestions[0] + "."
    if not context["outcomes_defined"]:
        return "Add outcome evidence before outreach or submission."
    if not context["budget_defined"]:
        return "Add budget range and program cost assumptions before screening award fit."
    if not context["partnerships_defined"]:
        return "Document partner roles before positioning this as a collaborative opportunity."
    return "Confirm requirements, decision-maker, and submission materials before moving into pursuit."


def _named_opportunity_rationale(item, context: dict) -> str:
    opportunity = item.opportunity
    reasons = _dedupe(item.match.reasons, 3)
    if reasons:
        rationale = f"{opportunity.name} is prioritized because of " + ", ".join(reasons).rstrip(".") + "."
    else:
        rationale = f"{opportunity.name} is prioritized because it is a named opportunity in the current inventory."
    if _geography_overlap(opportunity.geography, context):
        rationale += " Geography matches the service area."
    if item.match.score >= 75:
        rationale += " Current readiness and match signals support near-term review."
    if opportunity.source_references:
        rationale += _record_source_label(opportunity.source_references)
    return rationale


def _opportunity_risk(match, context: dict) -> str:
    if match.missing_factors:
        return match.missing_factors[0] + " may reduce competitiveness."
    if not context["funding_defined"]:
        return "Limited funding history may weaken credibility with funders."
    if not context["partnerships_defined"]:
        return "Limited partnership evidence may weaken collaborative fit."
    return "No major strategic risk is visible, but eligibility should still be verified."


def _opportunity_insights(discovery, context: dict) -> list[SnapshotOpportunityInsight]:
    insights = []
    for item in discovery.top_opportunities[:5]:
        match = item.match
        factors = _factor_summary(match.match_factors, ["Mission Alignment"])
        rationale = _named_opportunity_rationale(item, context)
        insights.append(
            SnapshotOpportunityInsight(
                name=item.opportunity.name,
                score=match.score,
                level=match.level,
                opportunity_type=item.opportunity.get_opportunity_type_display(),
                priority=item.opportunity.get_priority_level_display(),
                rationale=rationale,
                why_now=_opportunity_timing(item),
                preparation_required=_opportunity_preparation(match, context),
                risks=_opportunity_risk(match, context),
                factors=factors,
                source_indicators=_opportunity_source_indicators(item, context),
            )
        )
    return insights


def _alignment_level(score: int) -> str:
    if score >= 90:
        return "Excellent Fit"
    if score >= 80:
        return "Strong Fit"
    if score >= 70:
        return "Promising Fit"
    return "Exploratory Fit"


def _funder_fit_insights(
    funder_pathways: list[SnapshotInsight],
    sector: dict,
    context: dict,
) -> list[SnapshotFunderFit]:
    prep = []
    if not context["outcomes_defined"]:
        prep.append(f"Add measurable {sector['label'].lower()} outcomes.")
    if not context["budget_defined"]:
        prep.append("Prepare a clear budget range and funding use.")
    if not context["partnerships_defined"]:
        prep.append("Document partner roles and referral pathways.")
    if not context["funding_defined"]:
        prep.append("List current and recent funding sources.")
    prep.append(f"Create a one-page {sector['label']} funding brief.")
    insights = _named_funder_fit_insights(sector, context)
    seen = {item.archetype.casefold() for item in insights}
    for index, pathway in enumerate(funder_pathways[:5]):
        if pathway.label.casefold() in seen:
            continue
        score = 92 - (index * 4)
        if "Community Foundations" in pathway.label:
            score = max(score, 88)
        if "Government" in pathway.label or "Workforce" in pathway.label:
            score = max(score, 90)
        rationale = (
            f"{pathway.label} fits because the profile points to {sector['label']} work"
            " with clear mission and beneficiary alignment."
        )
        if context["geography"]:
            rationale += f" The fit can be localized around {context['geography'][0]}."
        insights.append(
            SnapshotFunderFit(
                archetype=pathway.label,
                alignment_level=_alignment_level(score),
                rationale=rationale,
                preparation_steps=_dedupe(prep, 3),
                source_indicators=[_alignment_level(score), "Archetype Fallback"],
            )
        )
        seen.add(pathway.label.casefold())
        if len(insights) >= 5:
            break
    return insights


def _ecosystem_gap_insights(relationship_targets: list[SnapshotInsight], sector: dict) -> list[SnapshotInsight]:
    insights = []
    for target in relationship_targets[:4]:
        label = target.label.replace("Pursue ", "Missing ")
        insights.append(
            SnapshotInsight(
                label,
                f"This gap matters because {target.rationale[0].lower() + target.rationale[1:]}",
                target.factors,
            )
        )
    if not insights:
        insights.append(
            SnapshotInsight(
                f"Missing {sector['label']} relationship map",
                "A named relationship map would make the Web of Opportunity more actionable.",
                ["Relationship Alignment", "Strategic Value"],
            )
        )
    return insights


def _readiness_context_insights(
    top_resource_gaps: list[str],
    top_risks_gaps: list[str],
    sector: dict,
) -> list[SnapshotInsight]:
    insights = []
    for gap in _dedupe(top_resource_gaps + top_risks_gaps, 5):
        if "No major" in gap:
            continue
        clean = gap.rstrip(".")
        consequence = (
            f"{clean} may reduce competitiveness for {sector['label'].lower()} opportunities "
            "because funders and partners need proof that the organization can execute."
        )
        if "partner" in clean.casefold() or "relationship" in clean.casefold():
            consequence = (
                f"{clean} may limit access to warm introductions, referral partners, and collaborative pathways."
            )
        elif "outcome" in clean.casefold() or "evidence" in clean.casefold():
            consequence = (
                f"{clean} may weaken the case for impact in grants, contracts, and partner conversations."
            )
        elif "budget" in clean.casefold() or "financial" in clean.casefold():
            consequence = (
                f"{clean} may make it harder to judge award-size fit and implementation capacity."
            )
        insights.append(
            SnapshotInsight(
                clean,
                consequence,
                ["Readiness Alignment", "Pursuit Risk"],
            )
        )
    return insights or [
        SnapshotInsight(
            "Maintain readiness evidence",
            f"Current readiness looks usable, but {sector['label'].lower()} pathways will still need current documents and proof.",
            ["Readiness Alignment"],
        )
    ]


def _action_insights(
    sector: dict,
    context: dict,
    top_opportunity_insights: list[SnapshotOpportunityInsight],
    funder_fit_insights: list[SnapshotFunderFit],
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
                f"Review pursuit fit for {opportunity.name}.",
                f"Highest-ranked named opportunity with {opportunity.level.lower()}; start with {opportunity.preparation_required.rstrip('.')}.",
                _factor_summary(opportunity.source_indicators + opportunity.factors, ["Opportunity Alignment"]),
            )
        )
    if funder_fit_insights:
        funder = funder_fit_insights[0]
        actions.append(
            SnapshotInsight(
                f"Prepare materials for {funder.archetype}.",
                f"{funder.alignment_level}; next step is {funder.preparation_steps[0].rstrip('.')}.",
                _factor_summary(funder.source_indicators, ["Funder Alignment"]),
            )
        )
    if relationship_targets:
        target = relationship_targets[0]
        if target.label.startswith("Strengthen "):
            relationship_action = target.label.replace("Strengthen ", "Initiate conversation with ", 1)
        elif target.label.startswith("Pursue "):
            relationship_action = target.label.replace("Pursue ", "Initiate conversation with ", 1)
        else:
            relationship_action = target.label
        actions.append(
            SnapshotInsight(
                relationship_action + ".",
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


def _reviewed_source_pages(project):
    from django.db.models import Q

    from openoutreach.signals.models import OrganizationSourcePage

    return list(
        OrganizationSourcePage.objects.filter(organization=project.organization)
        .filter(Q(project__isnull=True) | Q(project=project))
        .order_by("-relevance", "-last_reviewed_at", "title")
    )


def _source_summary(project) -> SnapshotSourceSummary:
    from openoutreach.funding.models import DocumentVaultItem, EvidenceLibraryItem, Funder, Opportunity, PartnerOrganization
    from openoutreach.signals.models import OrganizationSourcePage

    source_pages = _reviewed_source_pages(project)
    documents = list(project.document_vault_items.exclude(status=DocumentVaultItem.Status.ARCHIVED))
    evidence_items = list(project.evidence_library_items.exclude(status=EvidenceLibraryItem.Status.ARCHIVED))
    pilot = getattr(project, "pilot_profile", None)

    source_types = []
    important_sources = []
    reviewed_count = 0

    for source in source_pages:
        if source.review_status != OrganizationSourcePage.ReviewStatus.ARCHIVED:
            source_types.append(source.get_source_type_display())
        if source.review_status in {
            OrganizationSourcePage.ReviewStatus.REVIEWED,
            OrganizationSourcePage.ReviewStatus.USED_IN_SNAPSHOT,
        }:
            reviewed_count += 1
        if source.relevance in {
            OrganizationSourcePage.Relevance.HIGH,
            OrganizationSourcePage.Relevance.MEDIUM,
        } and source.review_status != OrganizationSourcePage.ReviewStatus.ARCHIVED:
            important_sources.append(source.title or source.url or source.get_source_type_display())

    available_document_types = {
        document.document_type
        for document in documents
        if document.status in {DocumentVaultItem.Status.AVAILABLE, DocumentVaultItem.Status.NEEDS_UPDATE}
    }
    for document in documents:
        if document.status in {DocumentVaultItem.Status.AVAILABLE, DocumentVaultItem.Status.NEEDS_UPDATE}:
            source_types.append(document.get_document_type_display())
            reviewed_count += 1
            important_sources.append(document.title)

    available_evidence_types = {
        evidence.evidence_type
        for evidence in evidence_items
        if evidence.status in {EvidenceLibraryItem.Status.AVAILABLE, EvidenceLibraryItem.Status.NEEDS_UPDATE}
    }
    for evidence in evidence_items:
        if evidence.status in {EvidenceLibraryItem.Status.AVAILABLE, EvidenceLibraryItem.Status.NEEDS_UPDATE}:
            source_types.append(evidence.get_evidence_type_display())
            reviewed_count += 1
            important_sources.append(evidence.title)

    if pilot:
        source_types.append("Discovery Questionnaire")
        if pilot.lifecycle_status != pilot.LifecycleStatus.WAITLIST:
            reviewed_count += 1
        if pilot.mission or pilot.primary_programs or pilot.top_goals:
            important_sources.append("Discovery questionnaire intake")

    source_type_keys = {source.source_type for source in source_pages}
    missing = []
    guidance = []
    if OrganizationSourcePage.SourceType.WEBSITE_PAGE not in source_type_keys and not project.organization.website:
        missing.append("Website Page")
        guidance.append("Add a website page or public profile to improve source transparency.")
    if DocumentVaultItem.DocumentType.STRATEGIC_PLAN not in available_document_types:
        missing.append("Strategic Plan")
        guidance.append("Add a strategic plan to improve readiness recommendations.")
    if OrganizationSourcePage.SourceType.PROGRAM_DESCRIPTION not in source_type_keys:
        missing.append("Program Description")
        guidance.append("Add program descriptions to improve opportunity matching.")
    if DocumentVaultItem.DocumentType.ANNUAL_REPORT not in available_document_types:
        missing.append("Annual Report")
        guidance.append("Add an annual report to strengthen credibility and impact context.")
    if OrganizationSourcePage.SourceType.GRANT_MATERIALS not in source_type_keys:
        missing.append("Grant Materials")
        guidance.append("Add recent grant materials to improve funding readiness.")
    if OrganizationSourcePage.SourceType.PARTNER_RESEARCH not in source_type_keys and not project.organization.existing_partnerships:
        missing.append("Partner Research")
        guidance.append("Add partner list or partner research to improve relationship recommendations.")
    if OrganizationSourcePage.SourceType.FUNDER_RESEARCH not in source_type_keys and not project.organization.current_funding_sources:
        missing.append("Funder Research")
        guidance.append("Add local funder research or funding history to sharpen pathway recommendations.")
    if EvidenceLibraryItem.EvidenceType.OUTCOME_METRIC not in available_evidence_types:
        missing.append("Outcome Evidence")
        guidance.append("Add outcome evidence so Snapshot recommendations feel more provable.")

    funders_reviewed = Funder.objects.filter(active=True).exclude(
        intelligence_status=Funder.IntelligenceStatus.ARCHIVED,
    ).count()
    opportunities_reviewed = Opportunity.objects.exclude(status=Opportunity.Status.ARCHIVED).count()
    ecosystem_entities_reviewed = PartnerOrganization.objects.filter(active=True).exclude(
        intelligence_status=PartnerOrganization.IntelligenceStatus.ARCHIVED,
    ).count()

    return SnapshotSourceSummary(
        sources_reviewed=reviewed_count,
        funders_reviewed=funders_reviewed,
        opportunities_reviewed=opportunities_reviewed,
        ecosystem_entities_reviewed=ecosystem_entities_reviewed,
        source_types_used=_dedupe(source_types, 8) or ["Organization Profile"],
        important_sources=_dedupe(important_sources, 5) or ["Organization profile and project narrative"],
        missing_source_types=_dedupe(missing, 6) or ["No major source gaps detected."],
        guidance=_dedupe(guidance, 5) or ["Keep source material current as the Snapshot moves toward delivery."],
    )


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
    relationship_target_insights = _relationship_target_insights(project, sector, context)
    top_opportunity_insights = _opportunity_insights(discovery, context)
    funder_fit_insights = _funder_fit_insights(funder_pathway_insights, sector, context)
    ecosystem_gap_insights = _ecosystem_gap_insights(relationship_target_insights, sector)
    readiness_context_insights = _readiness_context_insights(top_resource_gaps, top_risks_gaps, sector)
    recommended_action_insights = _action_insights(
        sector,
        context,
        top_opportunity_insights,
        funder_fit_insights,
        relationship_target_insights,
        top_resource_gaps,
        top_risks_gaps,
        actions,
    )
    source_summary = _source_summary(project)
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
        source_summary=source_summary,
        funder_fit_insights=funder_fit_insights,
        ecosystem_gap_insights=ecosystem_gap_insights,
        readiness_context_insights=readiness_context_insights,
    )
