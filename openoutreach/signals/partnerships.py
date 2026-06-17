from dataclasses import dataclass


PARTNERSHIP_ECOSYSTEM_ITEMS = [
    "Reach",
    "Credibility",
    "Referral pathways",
    "Service delivery capacity",
    "Funding competitiveness",
    "Program sustainability",
    "Community trust",
]


@dataclass(frozen=True)
class PartnershipCategory:
    name: str
    explanation: str


@dataclass(frozen=True)
class PartnerRecommendation:
    name: str
    score: int
    explanation: str


@dataclass(frozen=True)
class PartnershipChecklistItem:
    label: str
    status: str
    status_class: str
    detail: str


@dataclass(frozen=True)
class PartnershipReadiness:
    readiness_score: int
    readiness_level: str
    strengths: list[str]
    gaps: list[str]
    categories: list[PartnershipCategory]
    recommendations: list[PartnerRecommendation]
    checklist: list[PartnershipChecklistItem]
    actions: list[str]
    ecosystem_items: list[str]


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


def _checklist_item(label: str, complete: bool, complete_detail: str, missing_detail: str) -> PartnershipChecklistItem:
    return PartnershipChecklistItem(
        label=label,
        status="Complete" if complete else "Missing",
        status_class="complete" if complete else "missing",
        detail=complete_detail if complete else missing_detail,
    )


def _categories(project, organization) -> list[PartnershipCategory]:
    context = organization.mission or project.programs or "the mission"
    return [
        PartnershipCategory("Nonprofit Collaborators", f"Peer nonprofits can expand delivery, referrals, and credibility around {context}."),
        PartnershipCategory("Universities & Colleges", "Higher education partners can support research, evaluation, fellows, interns, and program design."),
        PartnershipCategory("Community Colleges", "Community colleges can strengthen workforce, credential, training, and employer-aligned pathways."),
        PartnershipCategory("Workforce Boards", "Workforce boards can connect training, placement, employer demand, and public workforce systems."),
        PartnershipCategory("Local Government Agencies", "Local agencies can support public-sector alignment, referrals, service contracts, and community initiatives."),
        PartnershipCategory("Public Libraries", "Libraries can support digital access, outreach, training space, and trusted neighborhood entry points."),
        PartnershipCategory("School Districts", "School districts can support youth access, referrals, career exposure, and family engagement."),
        PartnershipCategory("Healthcare Organizations", "Healthcare partners can support human services referrals, community benefit, and wraparound care."),
        PartnershipCategory("Corporate Partners", "Corporate partners can support volunteers, mentors, sponsorships, jobs, technology, and expertise."),
        PartnershipCategory("Foundations", "Foundations can support credibility, convening, co-funding, and strategic relationships."),
        PartnershipCategory("Faith-Based Organizations", "Faith-based organizations can support outreach, trust, facilities, volunteers, and local referrals."),
        PartnershipCategory("Community-Based Organizations", "Community-based organizations can strengthen reach, trust, neighborhood insight, and service coordination."),
    ]


def _recommendations() -> list[PartnerRecommendation]:
    return [
        PartnerRecommendation("Workforce Development Boards", 94, "Strong fit for career readiness, training, credentials, employer connections, and placement outcomes."),
        PartnerRecommendation("Universities & Colleges", 88, "Useful for evaluation, research, interns, fellows, clinics, and specialized program support."),
        PartnerRecommendation("Community Colleges", 90, "High-fit partners for credentials, bridge programs, workforce training, and local employer pathways."),
        PartnerRecommendation("Local Government Agencies", 86, "Relevant for public initiatives, referrals, service delivery, community development, and contracts."),
        PartnerRecommendation("Public Libraries", 82, "Useful for digital access, trusted outreach, workshops, and neighborhood-based program delivery."),
        PartnerRecommendation("School Districts", 80, "Relevant for youth pipeline, student referrals, family engagement, and career exposure."),
        PartnerRecommendation("Corporate Social Impact Teams", 78, "Useful for volunteers, mentors, sponsorships, skill-based support, and employment pathways."),
        PartnerRecommendation("Community Foundations", 84, "Relevant for convening, local credibility, funder introductions, and aligned initiatives."),
        PartnerRecommendation("Nonprofit Coalitions", 81, "Useful for shared advocacy, referrals, collective impact, and coordinated service delivery."),
        PartnerRecommendation("Healthcare / Human Services Providers", 76, "Relevant for wraparound referrals, community benefit, social needs, and trust-building."),
        PartnerRecommendation("Faith-Based Networks", 72, "Useful for local trust, volunteers, facilities, and community outreach."),
        PartnerRecommendation("Community-Based Organizations", 83, "Strong fit for reach, neighborhood trust, referrals, and culturally grounded implementation."),
    ]


def _actions(checklist: list[PartnershipChecklistItem]) -> list[str]:
    missing = {item.label for item in checklist if item.status == "Missing"}
    actions = []
    if "One-Page Partnership Brief" in missing:
        actions.append("Create a one-page partnership brief describing mission, programs, population, geography, outcomes, and partner asks.")
    if "Existing Partnerships" in missing:
        actions.append("Document existing partners and relationship history, including informal referrals and shared activities.")
    if "Local Contact Strategy" in missing:
        actions.append("Identify local anchor institutions aligned with the mission.")
    if "Partnership Goals" in missing:
        actions.append("Define partnership goals for each program, such as referrals, volunteers, facilities, employer access, or credibility.")
    if "Collaboration Capacity" in missing:
        actions.append("Map workforce, education, government, and community partner categories before outreach.")
    if "Outcomes / Impact" in missing:
        actions.append("Add measurable outcomes to support credibility with future partners.")
    actions.append("Build a local contact strategy with priority organizations, warm introductions, and next-step owners.")
    actions.append("Create a simple partner tracker for status, relationship owner, partner value, and next action.")
    return actions[:8]


def build_partnership_readiness(project, funding_criteria=None) -> PartnershipReadiness:
    organization = project.organization
    score = 35
    strengths = []
    gaps = []

    if organization.mission.strip():
        strengths.append("Mission clarity supports partner alignment and outreach.")
        score += 9
    else:
        gaps.append("Add a mission statement before partner outreach.")

    if project.programs.strip():
        strengths.append("Program definition makes partner roles easier to explain.")
        score += 10
    else:
        gaps.append("Define programs before mapping partner roles.")

    if organization.city or organization.county or organization.state or organization.service_area_notes:
        strengths.append("Service geography supports local anchor institution mapping.")
        score += 8
    else:
        gaps.append("Add service geography for local partner targeting.")

    target_population_ready = _has_values(organization.beneficiaries) or bool(
        funding_criteria and _has_values(funding_criteria.beneficiaries)
    )
    if target_population_ready:
        strengths.append("Target population is clear for referral and collaboration partners.")
        score += 8
    else:
        gaps.append("Add beneficiaries or target population language.")

    if _has_values(organization.outcomes_and_impact):
        strengths.append("Outcome evidence can increase credibility with partners.")
        score += 8
    else:
        gaps.append("Add outcomes or impact evidence.")

    if organization.budget_range.strip():
        strengths.append("Budget range gives partners context on scale and sustainability.")
        score += 5
    else:
        gaps.append("Add budget range or operating scale.")

    if _has_values(organization.existing_partnerships):
        strengths.append("Existing partnerships provide a starting relationship map.")
        score += 10
    else:
        gaps.append("Document existing partners and relationship history.")

    if _has_values(organization.current_funding_sources):
        strengths.append("Current funding sources can improve partner confidence and funding competitiveness.")
        score += 5
    else:
        gaps.append("Add current funding sources.")

    if str(organization.organization_type or "").strip():
        strengths.append("Organization type is clear for partner eligibility and role definition.")
        score += 7
    else:
        gaps.append("Add organization type or legal structure.")

    score = max(0, min(score, 100))
    checklist = [
        _checklist_item("Mission Clarity", bool(organization.mission.strip()), "Mission is clear enough for partner outreach.", "Add a concise mission statement."),
        _checklist_item("Program Definition", bool(project.programs.strip()), "Programs are defined for partner-role mapping.", "Add program activities and delivery model."),
        _checklist_item("Service Geography", bool(organization.city or organization.county or organization.state or organization.service_area_notes), "Geography is available for local partner mapping.", "Add city, county, state, or service-area notes."),
        _checklist_item("Target Population", target_population_ready, "Target population is clear for referral partners.", "Add beneficiaries or target population language."),
        _checklist_item("Outcomes / Impact", _has_values(organization.outcomes_and_impact), "Outcome evidence is available for credibility.", "Add outcomes, metrics, or evaluation notes."),
        _checklist_item("Existing Partnerships", _has_values(organization.existing_partnerships), "Existing partnerships are documented.", "Document existing partners and relationship history."),
        _checklist_item("Partnership Goals", False, "Partnership goals are defined.", "Define goals for referrals, service delivery, credibility, funding, or reach."),
        _checklist_item("Collaboration Capacity", _has_values(organization.existing_partnerships) and bool(project.programs.strip()), "Basic collaboration capacity is visible.", "Clarify staff capacity, partner owner, and collaboration process."),
        _checklist_item("One-Page Partnership Brief", False, "One-page partnership brief is ready.", "Create a concise partnership brief."),
        _checklist_item("Local Contact Strategy", bool(organization.city or organization.county or _has_values(organization.existing_partnerships)), "Local contact strategy can begin from geography and relationships.", "Build a local contact strategy."),
    ]
    return PartnershipReadiness(
        readiness_score=score,
        readiness_level=_level(score),
        strengths=strengths,
        gaps=gaps,
        categories=_categories(project, organization),
        recommendations=_recommendations(),
        checklist=checklist,
        actions=_actions(checklist),
        ecosystem_items=PARTNERSHIP_ECOSYSTEM_ITEMS,
    )
