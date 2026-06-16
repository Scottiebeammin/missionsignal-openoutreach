from dataclasses import dataclass, field


LOCAL_GOVERNMENT_DETAILS = [
    "City grants",
    "County grants",
    "youth services funding",
    "workforce programs",
    "economic development programs",
    "digital equity initiatives",
    "community development programs",
    "Public-sector service contracts",
    "RFPs",
]


THEME_RULES = [
    ("Workforce Development", ("workforce", "employment", "job", "career", "training")),
    ("Digital Equity", ("digital", "technology", "internet", "broadband", "device", "skills")),
    ("Youth Development", ("youth", "young people", "children", "student", "teen")),
    ("Career Readiness", ("career", "credential", "mentor", "readiness", "placement")),
    ("Community Development", ("community", "neighborhood", "economic mobility", "resident")),
    ("Education", ("education", "school", "learning", "student")),
    ("Small Business Support", ("small business", "entrepreneur", "business coaching")),
    ("Economic Mobility", ("economic mobility", "income", "wealth", "mobility")),
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
    status_class: str
    detail: str


@dataclass(frozen=True)
class LocalGovernmentSnapshot:
    heading: str
    relevance: str
    opportunity_lanes: list[str]
    next_step: str


@dataclass(frozen=True)
class FundingReadiness:
    readiness_score: int
    readiness_level: str
    strengths: list[str]
    gaps: list[str]
    funding_themes: list[str]
    recommended_funder_types: list[FunderRecommendation]
    local_government_snapshot: LocalGovernmentSnapshot
    grant_readiness_checklist: list[ChecklistItem]
    recommended_funding_actions: list[str]


def _has_values(values) -> bool:
    return any(str(value).strip() for value in values or [])


def _title_case(value: str) -> str:
    return " ".join(word.capitalize() for word in value.split())


def _combined_text(project, organization, funding_criteria) -> str:
    values = [
        organization.mission,
        project.programs,
        str(organization.organization_type or ""),
        organization.city,
        organization.county,
        organization.state,
        organization.service_area_notes,
        *(organization.beneficiaries or []),
        *(organization.capabilities or []),
        *(organization.outcomes_and_impact or []),
        *(organization.current_funding_sources or []),
        *(organization.existing_partnerships or []),
    ]
    if funding_criteria:
        values.extend(funding_criteria.focus_areas or [])
        values.extend(funding_criteria.beneficiaries or [])
        values.extend(funding_criteria.program_areas or [])
        values.extend(funding_criteria.funding_use_categories or [])
    return "\n".join(str(value) for value in values if value).casefold()


def _theme_values(project, organization, funding_criteria) -> list[str]:
    combined = _combined_text(project, organization, funding_criteria)
    values = []
    for label, terms in THEME_RULES:
        if any(term in combined for term in terms):
            values.append(label)

    sources = [
        getattr(funding_criteria, "focus_areas", None) if funding_criteria else None,
        organization.focus_areas,
        getattr(funding_criteria, "program_areas", None) if funding_criteria else None,
    ]
    known = {label.casefold() for label, _ in THEME_RULES}
    for source in sources:
        for value in source or []:
            clean = _title_case(str(value).strip())
            if clean and clean.casefold() not in known and clean not in values:
                values.append(clean)
    if values:
        return values
    return ["Mission-Aligned Services", "Community Impact", "Program Capacity"]


def _readiness_level(score: int) -> str:
    if score >= 85:
        return "Strong"
    if score >= 70:
        return "Ready with gaps"
    if score >= 50:
        return "Needs preparation"
    return "Early readiness"


def _checklist_item(label: str, complete: bool, complete_detail: str, missing_detail: str) -> ChecklistItem:
    return ChecklistItem(
        label=label,
        status="Complete" if complete else "Missing",
        status_class="complete" if complete else "missing",
        detail=complete_detail if complete else missing_detail,
    )


def _specific_actions(checklist: list[ChecklistItem], organization, project) -> list[str]:
    actions = []
    missing = {item.label for item in checklist if item.status == "Missing"}
    if "Mission Statement" in missing:
        actions.append("Write a two-sentence mission statement that names the population served and the change the program creates.")
    if "Programs Defined" in missing:
        actions.append("Define the primary program model, including activities, participant flow, and delivery partners.")
    if "Organization Type" in missing:
        actions.append("Confirm the organization type, legal structure, and nonprofit or fiscal-sponsor status before screening grants.")
    if "Service Geography" in missing:
        actions.append("Add city, county, state, and service-area notes so Local Government lanes can be matched cleanly.")
    if "Target Population" in missing:
        actions.append("Name the target population in funder language, such as youth, job seekers, students, families, or small businesses.")
    if "Outcomes / Impact" in missing:
        actions.append("Collect two or three outcome metrics, such as credential completion, placement, retention, or participant reach.")
    if "Budget Range" in missing:
        actions.append("Prepare a simple program budget range with staffing, direct service, technology, and evaluation costs.")
    if "Current Funding Sources" in missing:
        actions.append("List current and recent funders, even small grants, contracts, earned revenue, or in-kind support.")
    if "Existing Partnerships" in missing:
        actions.append("Document active partners and their roles so collaborative city, county, and workforce applications are easier to justify.")

    actions.append("Use the Local Government snapshot to shortlist city, county, workforce, economic development, and digital equity lanes before broad grant search.")
    actions.append(f"Turn {project.name} into a one-page funding brief with themes, geography, outcomes, budget, and partner evidence.")
    return actions[:7]


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

    local_government_snapshot = LocalGovernmentSnapshot(
        heading="Local Government Opportunity Snapshot",
        relevance=(
            f"Local Government is a core funding lane for {local_context} because public agencies "
            "often fund direct services, workforce systems, youth supports, digital access, and "
            "community development through grants, contracts, and RFPs."
        ),
        opportunity_lanes=LOCAL_GOVERNMENT_DETAILS,
        next_step=(
            "Start by mapping city departments, county agencies, workforce boards, economic "
            "development offices, and digital equity programs connected to the service geography."
        ),
    )

    recommended_funder_types = [
        FunderRecommendation(
            "Local Government",
            95,
            (
                f"Best first government lane for {local_context}; strongest fit for public-sector "
                "grants, contracts, and RFPs tied to community outcomes."
            ),
            LOCAL_GOVERNMENT_DETAILS,
        ),
        FunderRecommendation(
            "Community Foundations",
            90,
            "Strong fit for locally anchored mission work, capacity building, and program grants.",
        ),
        FunderRecommendation(
            "Workforce Development Boards",
            88,
            "Strong fit when programs include career readiness, training, job placement, or employer partnerships.",
        ),
        FunderRecommendation(
            "Corporate Foundations",
            82,
            "Useful for workforce, education, digital inclusion, and community investment priorities.",
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
        _checklist_item(
            "Mission Statement",
            bool(organization.mission.strip()),
            "Mission statement is available for funder-facing summaries.",
            "Add a concise mission statement.",
        ),
        _checklist_item(
            "Programs Defined",
            bool(project.programs.strip()),
            "Program description is ready for opportunity screening.",
            "Add the core program model and activities.",
        ),
        _checklist_item(
            "Organization Type",
            bool(str(organization.organization_type or "").strip()),
            "Organization type is available for eligibility review.",
            "Add organization type, legal structure, or nonprofit status.",
        ),
        _checklist_item(
            "Service Geography",
            bool(organization.city or organization.county or organization.state or organization.service_area_notes),
            "Service geography is available for local and regional targeting.",
            "Add city, county, state, or service-area notes.",
        ),
        _checklist_item(
            "Target Population",
            _has_values(organization.beneficiaries) or bool(funding_criteria and _has_values(funding_criteria.beneficiaries)),
            "Target population is clear enough for funder fit review.",
            "Add the populations served, such as youth, job seekers, students, families, or small businesses.",
        ),
        _checklist_item(
            "Outcomes / Impact",
            _has_values(organization.outcomes_and_impact),
            "Outcome evidence is available for readiness review.",
            "Add outcome metrics, evaluation notes, or participant results.",
        ),
        _checklist_item(
            "Budget Range",
            bool(organization.budget_range.strip()),
            "Budget range is available for award-size fit.",
            "Add a budget range or project budget target.",
        ),
        _checklist_item(
            "Current Funding Sources",
            _has_values(organization.current_funding_sources),
            "Funding history is available for credibility review.",
            "Add current or recent funding sources.",
        ),
        _checklist_item(
            "Existing Partnerships",
            _has_values(organization.existing_partnerships),
            "Partnerships are available for collaborative funding narratives.",
            "Add existing partners and their roles.",
        ),
    ]

    recommended_funding_actions = _specific_actions(checklist=grant_readiness_checklist, organization=organization, project=project)

    return FundingReadiness(
        readiness_score=score,
        readiness_level=_readiness_level(score),
        strengths=strengths,
        gaps=gaps,
        funding_themes=funding_themes,
        recommended_funder_types=recommended_funder_types,
        local_government_snapshot=local_government_snapshot,
        grant_readiness_checklist=grant_readiness_checklist,
        recommended_funding_actions=recommended_funding_actions,
    )
