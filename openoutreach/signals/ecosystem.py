from dataclasses import dataclass


@dataclass(frozen=True)
class SignalScorecard:
    name: str
    score: int
    level: str
    status: str
    href_name: str
    detail: str


@dataclass(frozen=True)
class EcosystemStatus:
    name: str
    status: str
    detail: str
    href_name: str


@dataclass(frozen=True)
class PriorityOpportunityArea:
    label: str
    reason: str
    next_step: str


@dataclass(frozen=True)
class EcosystemRoadmap:
    completed: list[str]
    coming_soon: list[str]
    future: list[str]


@dataclass(frozen=True)
class EcosystemOverview:
    score: int
    level: str
    signal_scorecards: list[SignalScorecard]
    statuses: list[EcosystemStatus]
    strengths: list[str]
    gaps: list[str]
    priority_areas: list[PriorityOpportunityArea]
    recommended_actions: list[str]
    match_overview: object | None
    discovery_overview: object | None
    summary_items: list[str]
    roadmap: EcosystemRoadmap


def _has_values(values) -> bool:
    return any(str(value).strip() for value in values or [])


def _level(score: int) -> str:
    if score >= 85:
        return "Advanced"
    if score >= 70:
        return "Competitive"
    if score >= 50:
        return "Developing"
    return "Emerging"


def _dedupe(values: list[str], limit: int) -> list[str]:
    seen = set()
    unique = []
    for value in values:
        clean = str(value).strip()
        key = clean.casefold()
        if clean and key not in seen:
            seen.add(key)
            unique.append(clean)
        if len(unique) >= limit:
            break
    return unique


def _mission_profile(project) -> tuple[int, list[str], list[str]]:
    organization = project.organization
    score = 20
    strengths = []
    gaps = []

    if organization.mission.strip():
        strengths.append("Clear mission")
        score += 15
    else:
        gaps.append("Mission statement missing")

    if project.programs.strip():
        strengths.append("Defined programs")
        score += 15
    else:
        gaps.append("Program model missing")

    if organization.city or organization.county or organization.state or organization.service_area_notes:
        strengths.append("Geographic focus")
        score += 12
    else:
        gaps.append("Service geography missing")

    if _has_values(organization.beneficiaries):
        strengths.append("Target population identified")
        score += 10
    else:
        gaps.append("Target population missing")

    if _has_values(organization.outcomes_and_impact):
        strengths.append("Outcomes evidence available")
        score += 10
    else:
        gaps.append("Outcomes missing")

    if organization.budget_range.strip():
        strengths.append("Budget range documented")
        score += 8
    else:
        gaps.append("Budget range missing")

    if _has_values(organization.current_funding_sources):
        strengths.append("Funding history documented")
        score += 5
    else:
        gaps.append("Funding sources missing")

    if _has_values(organization.existing_partnerships):
        strengths.append("Existing partnerships documented")
        score += 5
    else:
        gaps.append("Existing partnerships missing")

    score = max(0, min(score, 100))
    return score, strengths, gaps


def _scorecard(name: str, readiness, href_name: str, detail: str) -> SignalScorecard:
    return SignalScorecard(
        name=name,
        score=readiness.readiness_score,
        level=readiness.readiness_level,
        status="Active",
        href_name=href_name,
        detail=detail,
    )


def _priority_area(label: str, score: int, fallback_reason: str, next_step: str) -> PriorityOpportunityArea:
    if score >= 80:
        reason = f"{label} is a strong lane to use now."
    elif score >= 65:
        reason = f"{label} is promising, with a few readiness gaps to close."
    else:
        reason = fallback_reason
    return PriorityOpportunityArea(label, reason, next_step)


def _missing_checklist_gaps(readiness) -> list[str]:
    checklist = (
        getattr(readiness, "grant_readiness_checklist", None)
        or getattr(readiness, "engagement_checklist", None)
        or getattr(readiness, "checklist", None)
        or []
    )
    return [
        f"{item.label} missing"
        for item in checklist
        if getattr(item, "status", "") == "Missing"
    ]


def _priority_areas(
    funding_readiness, government_readiness, resource_readiness, partnership_readiness, gaps: list[str],
) -> list[PriorityOpportunityArea]:
    gap_text = " ".join(gaps).casefold()
    areas = [
        _priority_area(
            "Funding Readiness",
            funding_readiness.readiness_score,
            "Funding work needs stronger evidence, budget, and funder-facing materials.",
            "Turn the project into a one-page funding brief with themes, outcomes, budget, and partner evidence.",
        ),
        _priority_area(
            "Government Engagement",
            government_readiness.readiness_score,
            "Government outreach needs clearer local targets, outcomes, and public-sector positioning.",
            "Map city, county, workforce, digital equity, and community development contacts tied to the service area.",
        ),
        _priority_area(
            "Resource Development",
            resource_readiness.readiness_score,
            "Resource development needs a clearer inventory of technology, volunteer, training, and capacity needs.",
            "Create a resource needs inventory that separates funding needs from non-funding supports.",
        ),
        _priority_area(
            "Partnership Development",
            partnership_readiness.readiness_score,
            "Partnership work needs defined goals, partner roles, and a local contact strategy.",
            "Create a one-page partnership brief and prioritize anchor institutions aligned with the mission.",
        ),
    ]
    if "capacity" in gap_text or "technology" in gap_text or "volunteer" in gap_text:
        areas.append(
            PriorityOpportunityArea(
                "Capacity Building",
                "Capacity gaps could limit the organization's ability to use funding, resource, and partnership opportunities well.",
                "Assess governance, finance, technology, volunteer, and delivery capacity needs for the next two quarters.",
            )
        )
    else:
        areas.append(
            PriorityOpportunityArea(
                "Capacity Building",
                "The ecosystem is ready for a more explicit capacity-building plan.",
                "Define priority capacity-building needs across operations, technology, evaluation, and staffing.",
            )
        )
    if "outcome" in gap_text or "impact" in gap_text:
        areas.append(
            PriorityOpportunityArea(
                "Outcomes Measurement",
                "Outcome evidence is one of the highest-leverage gaps across funding, government, resources, and partnerships.",
                "Add measurable outcomes before deeper grant, contract, resource, or partner outreach.",
            )
        )
    else:
        areas.append(
            PriorityOpportunityArea(
                "Outcomes Measurement",
                "Outcome evidence is already present and can strengthen every opportunity lane.",
                "Package the strongest outcome metrics into funding, government, resource, and partnership briefs.",
            )
        )
    return areas


def _recommended_actions(project, module_readiness: list, gaps: list[str]) -> list[str]:
    gap_text = " ".join(gaps).casefold()
    actions = []

    if "outcome" in gap_text or "impact" in gap_text:
        actions.append("Add measurable outcomes to improve funding, government, resource, and partnership readiness.")
    if "budget" in gap_text or "funding source" in gap_text:
        actions.append("Document budget range and funding history.")
    if "partnership" in gap_text or "brief" in gap_text:
        actions.append("Create a one-page partnership and government engagement brief.")
    if "contact" in gap_text or "geograph" in gap_text:
        actions.append("Build a local contact map for funders, agencies, and partner organizations.")
    if "resource" in gap_text or "technology" in gap_text or "capacity" in gap_text:
        actions.append("Create a resource needs inventory.")

    for readiness in module_readiness:
        for action in (
            getattr(readiness, "recommended_funding_actions", None)
            or getattr(readiness, "recommended_actions", None)
            or getattr(readiness, "actions", None)
            or []
        ):
            actions.append(action)

    actions.append(f"Use {project.name} as the shared organizing brief across all opportunity lanes.")
    return _dedupe(actions, 8)


def build_ecosystem_overview(
    project, funding_readiness, government_readiness, resource_readiness,
    partnership_readiness, match_overview=None, discovery_overview=None,
) -> EcosystemOverview:
    mission_score, mission_strengths, mission_gaps = _mission_profile(project)
    signal_scorecards = [
        SignalScorecard(
            "Mission Brief",
            mission_score,
            _level(mission_score),
            "Active",
            "project-mission-brief",
            "Mission profile, project narrative, geography, beneficiaries, and readiness gaps.",
        ),
        _scorecard(
            "FundingSignal",
            funding_readiness,
            "project-funding",
            "Funding themes, funder types, Local Government lanes, checklist, and actions.",
        ),
        _scorecard(
            "GovernmentSignal",
            government_readiness,
            "project-government",
            "Public-sector lanes, government entity types, checklist, and actions.",
        ),
        _scorecard(
            "ResourceSignal",
            resource_readiness,
            "project-resources",
            "Non-funding resources, capacity supports, checklist, and actions.",
        ),
        _scorecard(
            "PartnershipSignal",
            partnership_readiness,
            "project-partnerships",
            "Partner categories, partner recommendations, checklist, and actions.",
        ),
    ]
    module_scores = [card.score for card in signal_scorecards]
    score = round(sum(module_scores) / len(module_scores))
    strengths = _dedupe(
        mission_strengths
        + ["Strong government alignment", "Strong funding theme alignment"]
        + funding_readiness.strengths
        + government_readiness.strengths
        + resource_readiness.strengths
        + partnership_readiness.strengths,
        12,
    )
    gaps = _dedupe(
        mission_gaps
        + funding_readiness.gaps
        + government_readiness.gaps
        + resource_readiness.gaps
        + partnership_readiness.gaps,
        8,
    )
    gaps = _dedupe(
        gaps
        + _missing_checklist_gaps(funding_readiness)
        + _missing_checklist_gaps(government_readiness)
        + _missing_checklist_gaps(resource_readiness)
        + _missing_checklist_gaps(partnership_readiness),
        12,
    )
    statuses = [
        EcosystemStatus(card.name, card.status, card.detail, card.href_name)
        for card in signal_scorecards
    ]
    module_readiness = [
        funding_readiness, government_readiness, resource_readiness, partnership_readiness,
    ]
    return EcosystemOverview(
        score=max(0, min(score, 100)),
        level=_level(score),
        signal_scorecards=signal_scorecards,
        statuses=statuses,
        strengths=strengths,
        gaps=gaps,
        priority_areas=_priority_areas(
            funding_readiness, government_readiness, resource_readiness, partnership_readiness, gaps,
        ),
        recommended_actions=_recommended_actions(project, module_readiness, gaps),
        match_overview=match_overview,
        discovery_overview=discovery_overview,
        summary_items=["Funding", "Government", "Resources", "Partnerships", "Capacity", "Risks and constraints"],
        roadmap=EcosystemRoadmap(
            completed=["Mission Brief", "FundingSignal", "GovernmentSignal", "ResourceSignal", "PartnershipSignal"],
            coming_soon=[],
            future=["Opportunity Discovery Engine", "Monitoring Systems", "AI Opportunity Agents"],
        ),
    )
