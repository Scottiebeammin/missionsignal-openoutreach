from dataclasses import dataclass, field


LOCAL_GOVERNMENT_DETAILS = [
    "city grants",
    "county grants",
    "youth services funding",
    "workforce programs",
    "economic development programs",
    "digital equity initiatives",
    "community development programs",
    "service contracts",
    "RFPs",
]


@dataclass(frozen=True)
class FunderRecommendation:
    name: str
    score: int
    explanation: str
    details: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ChecklistItem:
    label: str
    status: str
    detail: str


@dataclass(frozen=True)
class FundingReadiness:
    readiness_score: int
    readiness_level: str
    strengths: list[str]
    gaps: list[str]
    funding_themes: list[str]
    recommended_funder_types: list[FunderRecommendation]
    grant_readiness_checklist: list[ChecklistItem]
    recommended_funding_actions: list[str]


def _has_values(values) -> bool:
    return any(str(value).strip() for value in values or [])


def _theme_values(project, organization, funding_criteria) -> list[str]:
    sources = [
        getattr(funding_criteria, "focus_areas", None) if funding_criteria else None,
        organization.focus_areas,
        getattr(funding_criteria, "program_areas", None) if funding_criteria else None,
        organization.capabilities,
    ]
    values = []
    for source in sources:
        for value in source or []:
            clean = str(value).strip()
            if clean and clean not in values:
                values.append(clean)
    if values:
        return values
    return ["mission-aligned services", "community impact", "program capacity"]


def _readiness_level(score: int) -> str:
    if score >= 85:
        return "Strong"
    if score >= 70:
        return "Ready with gaps"
    if score >= 50:
        return "Needs preparation"
    return "Early readiness"


def build_funding_readiness(project, funding_criteria=None) -> FundingReadiness:
    organization = project.organization
    strengths = []
    gaps = []
    score = 45

    if _has_values(_theme_values(project, organization, funding_criteria)):
        strengths.append("Mission and program themes are clear enough to guide funder targeting.")
        score += 12
    else:
        gaps.append("Clarify mission and program themes before opportunity matching.")

    if organization.city or organization.county or organization.state or organization.service_area_notes:
        strengths.append("Service geography is defined for local and regional funder filters.")
        score += 12
    else:
        gaps.append("Add city, county, state, or service-area notes.")

    if _has_values(organization.outcomes_and_impact):
        strengths.append("Outcome evidence is available for grant narratives.")
        score += 10
    else:
        gaps.append("Add outcome metrics, impact evidence, or evaluation notes.")

    if organization.budget_range:
        strengths.append("Budget range is available for award-size fit.")
        score += 8
    else:
        gaps.append("Add an annual budget range or project budget target.")

    if _has_values(organization.current_funding_sources):
        strengths.append("Current funding history can support credibility review.")
        score += 7
    else:
        gaps.append("Add current or past funding sources.")

    if _has_values(organization.existing_partnerships):
        strengths.append("Existing partnerships can support collaborative applications.")
        score += 6
    else:
        gaps.append("Add partner organizations, referral sources, or employer relationships.")

    if funding_criteria and funding_criteria.inclusion_criteria:
        strengths.append("Deterministic funding criteria have been generated for review.")
        score += 5
    else:
        gaps.append("Run analysis to generate initial funding criteria.")

    score = max(0, min(score, 100))
    funding_themes = _theme_values(project, organization, funding_criteria)
    local_context = ", ".join(
        value for value in [organization.city, organization.county, organization.state] if value
    )
    if not local_context:
        local_context = "the project's service area"

    recommended_funder_types = [
        FunderRecommendation(
            "Community Foundations",
            90,
            "Strong fit for locally anchored mission work, capacity building, and program grants.",
        ),
        FunderRecommendation(
            "Corporate Foundations",
            82,
            "Useful for workforce, education, digital inclusion, and community investment priorities.",
        ),
        FunderRecommendation(
            "Local Government",
            95,
            (
                f"Best first government lane for {local_context}; includes city grants, county grants, "
                "youth services funding, workforce programs, economic development programs, digital "
                "equity initiatives, community development programs, service contracts, and RFPs."
            ),
            LOCAL_GOVERNMENT_DETAILS,
        ),
        FunderRecommendation(
            "State Government",
            84,
            "Relevant for workforce systems, youth programs, education initiatives, and regional pilots.",
        ),
        FunderRecommendation(
            "Federal Government",
            72,
            "Higher effort opportunities suited to mature programs with compliance capacity.",
        ),
        FunderRecommendation(
            "Workforce Development Boards",
            88,
            "Strong fit when programs include career readiness, training, job placement, or employer partnerships.",
        ),
        FunderRecommendation(
            "United Way Organizations",
            80,
            "Relevant for community impact, youth support, family stability, and local service coordination.",
        ),
        FunderRecommendation(
            "Family Foundations",
            78,
            "Good fit for relationship-led local giving and mission-aligned program support.",
        ),
    ]

    grant_readiness_checklist = [
        ChecklistItem(
            "Mission and program narrative",
            "Ready" if project.programs and organization.mission else "Needs work",
            "Use the Mission Brief and program description as the base narrative.",
        ),
        ChecklistItem(
            "Funding themes",
            "Ready" if funding_themes else "Needs work",
            "Confirm the generated themes before matching opportunities.",
        ),
        ChecklistItem(
            "Service geography",
            "Ready" if organization.city or organization.county or organization.state else "Needs work",
            "Local funders need city, county, state, and service-area clarity.",
        ),
        ChecklistItem(
            "Outcomes and impact evidence",
            "Ready" if _has_values(organization.outcomes_and_impact) else "Gap",
            "Add metrics, stories, evaluation results, or placement data.",
        ),
        ChecklistItem(
            "Budget and funding history",
            "Ready" if organization.budget_range and _has_values(organization.current_funding_sources) else "Gap",
            "Add budget range and current funding sources for credibility and award-size fit.",
        ),
        ChecklistItem(
            "Partnership evidence",
            "Ready" if _has_values(organization.existing_partnerships) else "Gap",
            "Add partner names and roles for collaborative grant opportunities.",
        ),
    ]

    recommended_funding_actions = [
        "Review and approve the generated funding themes.",
        "Prioritize Local Government opportunities before broad grant search.",
        "Prepare a one-page program budget and outcome summary.",
        "Gather evidence for any checklist item marked Gap.",
        "Use GovernmentSignal to plan city, county, state, and federal public-sector lanes.",
    ]

    return FundingReadiness(
        readiness_score=score,
        readiness_level=_readiness_level(score),
        strengths=strengths,
        gaps=gaps,
        funding_themes=funding_themes,
        recommended_funder_types=recommended_funder_types,
        grant_readiness_checklist=grant_readiness_checklist,
        recommended_funding_actions=recommended_funding_actions,
    )
