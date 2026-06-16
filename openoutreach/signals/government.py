from dataclasses import dataclass


PUBLIC_SECTOR_LANES = [
    "City Grants",
    "County Grants",
    "Workforce Programs",
    "Youth Services Funding",
    "Economic Development Programs",
    "Digital Equity Initiatives",
    "Community Development Programs",
    "Public-Sector Service Contracts",
    "RFPs / Procurement Opportunities",
]


@dataclass(frozen=True)
class GovernmentEntityRecommendation:
    name: str
    score: int
    explanation: str


@dataclass(frozen=True)
class GovernmentChecklistItem:
    label: str
    status: str
    status_class: str
    detail: str


@dataclass(frozen=True)
class GovernmentReadiness:
    readiness_score: int
    readiness_level: str
    strengths: list[str]
    gaps: list[str]
    public_sector_lanes: list[str]
    recommended_entity_types: list[GovernmentEntityRecommendation]
    engagement_checklist: list[GovernmentChecklistItem]
    recommended_actions: list[str]


def _has_values(values) -> bool:
    return any(str(value).strip() for value in values or [])


def _checklist_item(label: str, complete: bool, complete_detail: str, missing_detail: str) -> GovernmentChecklistItem:
    return GovernmentChecklistItem(
        label=label,
        status="Complete" if complete else "Missing",
        status_class="complete" if complete else "missing",
        detail=complete_detail if complete else missing_detail,
    )


def _readiness_level(score: int) -> str:
    if score >= 85:
        return "Strong"
    if score >= 70:
        return "Ready with gaps"
    if score >= 50:
        return "Needs preparation"
    return "Early readiness"


def _local_context(organization) -> str:
    context = ", ".join(
        value for value in [organization.city, organization.county, organization.state] if value
    )
    if context:
        return context
    if organization.service_area_notes:
        return organization.service_area_notes
    return "the project's service area"


def _target_population_available(organization, funding_criteria) -> bool:
    return _has_values(organization.beneficiaries) or bool(
        funding_criteria and _has_values(funding_criteria.beneficiaries)
    )


def _specific_actions(checklist: list[GovernmentChecklistItem], organization, project) -> list[str]:
    missing = {item.label for item in checklist if item.status == "Missing"}
    actions = []

    if "Service Geography" in missing:
        actions.append("Define the city, county, state, and service-area boundaries before approaching public agencies.")
    else:
        actions.append("Map city and county departments aligned with the mission and service geography.")

    if "Program Description" in missing:
        actions.append("Turn the program model into a public-sector brief with activities, participant flow, and delivery capacity.")
    if "Target Population" in missing:
        actions.append("Name the target population in public-agency language, such as youth, job seekers, residents, students, or families.")
    if "Outcomes / Impact" in missing:
        actions.append("Document program outcomes before pursuing contracts, service agreements, or RFP responses.")
    if "Budget Range" in missing:
        actions.append("Prepare a program budget range that separates staffing, direct service, technology, and evaluation costs.")
    if "Public-Sector Partnership History" in missing:
        actions.append("List any city, county, school, library, or workforce relationships, even if they are informal.")
    if "Contract / Grant Readiness" in missing:
        actions.append("Create a one-page government partnership brief with mission, program, geography, outcomes, budget, and partners.")
    if "Local Contact Strategy" in missing:
        actions.append("Identify workforce board contacts, youth services leads, economic development staff, and digital equity program owners.")

    actions.append("Track local RFP and procurement portals for service contracts and pilot opportunities.")
    actions.append(f"Use FundingSignal themes to decide which GovernmentSignal lanes fit {project.name} first.")
    return actions[:8]


def build_government_readiness(project, funding_criteria=None) -> GovernmentReadiness:
    organization = project.organization
    strengths = []
    gaps = []
    score = 35

    if organization.mission.strip():
        strengths.append("Mission statement is available for public-sector positioning.")
        score += 8
    else:
        gaps.append("Add a mission statement before government outreach.")

    if project.programs.strip():
        strengths.append("Program description is available for grants, contracts, and RFP screening.")
        score += 10
    else:
        gaps.append("Define the program model and delivery capacity.")

    if str(organization.organization_type or "").strip():
        strengths.append("Organization type is available for eligibility review.")
        score += 7
    else:
        gaps.append("Add organization type, legal structure, or nonprofit status.")

    if organization.city or organization.county or organization.state or organization.service_area_notes:
        strengths.append("Service geography is clear enough to map city, county, and regional agencies.")
        score += 12
    else:
        gaps.append("Add city, county, state, or service-area notes.")

    if _target_population_available(organization, funding_criteria):
        strengths.append("Target population is clear for public agency alignment.")
        score += 8
    else:
        gaps.append("Add beneficiaries or target population language.")

    if _has_values(organization.outcomes_and_impact):
        strengths.append("Outcome evidence can support grant and contract narratives.")
        score += 10
    else:
        gaps.append("Add outcomes, impact metrics, or evaluation evidence.")

    if organization.budget_range.strip():
        strengths.append("Budget range supports award-size and contract-fit review.")
        score += 7
    else:
        gaps.append("Add budget range or project cost assumptions.")

    if _has_values(organization.existing_partnerships):
        strengths.append("Partnership history can support public-sector credibility.")
        score += 6
    else:
        gaps.append("Add existing partnerships or public-sector relationships.")

    if _has_values(organization.current_funding_sources):
        strengths.append("Current funding sources help establish readiness and credibility.")
        score += 5
    else:
        gaps.append("Add current or recent funding sources.")

    score = max(0, min(score, 100))
    local_context = _local_context(organization)
    recommended_entity_types = [
        GovernmentEntityRecommendation(
            "City Government",
            94,
            f"Strong first lane for departments serving {local_context}, especially youth, workforce, digital equity, and community development programs.",
        ),
        GovernmentEntityRecommendation(
            "County Government",
            90,
            "Relevant for countywide human services, workforce systems, community development, and service contracts.",
        ),
        GovernmentEntityRecommendation(
            "Workforce Development Boards",
            88,
            "High-fit entity when programs involve career readiness, training, placement, employer partnerships, or credentials.",
        ),
        GovernmentEntityRecommendation(
            "Economic Development Agencies",
            84,
            "Useful for economic mobility, entrepreneurship, business support, and neighborhood revitalization lanes.",
        ),
        GovernmentEntityRecommendation(
            "Public School Districts",
            78,
            "Relevant for youth programming, career exposure, mentoring, digital skills, and student support partnerships.",
        ),
        GovernmentEntityRecommendation(
            "Public Libraries",
            76,
            "Relevant for digital access, community learning, workforce navigation, and neighborhood outreach.",
        ),
        GovernmentEntityRecommendation(
            "Housing / Community Development Agencies",
            82,
            "Relevant when programs support residents, neighborhood stability, economic mobility, or community development outcomes.",
        ),
        GovernmentEntityRecommendation(
            "Regional Planning Agencies",
            70,
            "Useful for regional workforce, transportation, broadband, equity, and economic development planning partnerships.",
        ),
    ]

    engagement_checklist = [
        _checklist_item(
            "Service Geography",
            bool(organization.city or organization.county or organization.state or organization.service_area_notes),
            "Geography is ready for city, county, and regional agency mapping.",
            "Add city, county, state, or service-area notes.",
        ),
        _checklist_item(
            "Program Description",
            bool(project.programs.strip()),
            "Program description is ready for public-sector screening.",
            "Add program activities, delivery model, and participant flow.",
        ),
        _checklist_item(
            "Target Population",
            _target_population_available(organization, funding_criteria),
            "Target population is clear enough for agency alignment.",
            "Add the population served using public-sector language.",
        ),
        _checklist_item(
            "Outcomes / Impact",
            _has_values(organization.outcomes_and_impact),
            "Outcome evidence is available for grants, contracts, and RFPs.",
            "Add outcome metrics, evaluation notes, or participant results.",
        ),
        _checklist_item(
            "Budget Range",
            bool(organization.budget_range.strip()),
            "Budget range is available for award and contract sizing.",
            "Add a budget range or project cost estimate.",
        ),
        _checklist_item(
            "Public-Sector Partnership History",
            _has_values(organization.existing_partnerships),
            "Partnership history is available for credibility review.",
            "Add city, county, school, library, workforce, or agency relationships.",
        ),
        _checklist_item(
            "Contract / Grant Readiness",
            bool(project.programs.strip() and organization.mission.strip() and _has_values(organization.outcomes_and_impact) and organization.budget_range.strip()),
            "Core narrative, outcomes, and budget are ready for public-sector pursuit.",
            "Complete program narrative, outcomes, and budget before pursuing contracts or grants.",
        ),
        _checklist_item(
            "Local Contact Strategy",
            bool(organization.city or organization.county or _has_values(organization.existing_partnerships)),
            "Local context is ready to start mapping contacts.",
            "Identify local departments, boards, agencies, and program owners.",
        ),
    ]

    return GovernmentReadiness(
        readiness_score=score,
        readiness_level=_readiness_level(score),
        strengths=strengths,
        gaps=gaps,
        public_sector_lanes=PUBLIC_SECTOR_LANES,
        recommended_entity_types=recommended_entity_types,
        engagement_checklist=engagement_checklist,
        recommended_actions=_specific_actions(engagement_checklist, organization, project),
    )
