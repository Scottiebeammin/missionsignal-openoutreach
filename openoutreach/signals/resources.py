from dataclasses import dataclass


RESOURCE_ECOSYSTEM_ITEMS = [
    "Training",
    "Technical assistance",
    "Volunteers",
    "Technology",
    "Facilities",
    "Equipment",
    "Capacity-building programs",
    "Shared services",
]


@dataclass(frozen=True)
class ResourceCategory:
    name: str
    explanation: str


@dataclass(frozen=True)
class ResourceRecommendation:
    name: str
    score: int
    explanation: str


@dataclass(frozen=True)
class ResourceChecklistItem:
    label: str
    status: str
    status_class: str
    detail: str


@dataclass(frozen=True)
class ResourceReadiness:
    readiness_score: int
    readiness_level: str
    strengths: list[str]
    gaps: list[str]
    categories: list[ResourceCategory]
    recommendations: list[ResourceRecommendation]
    checklist: list[ResourceChecklistItem]
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


def _checklist_item(label: str, complete: bool, complete_detail: str, missing_detail: str) -> ResourceChecklistItem:
    return ResourceChecklistItem(
        label=label,
        status="Complete" if complete else "Missing",
        status_class="complete" if complete else "missing",
        detail=complete_detail if complete else missing_detail,
    )


def _resource_categories(project, organization) -> list[ResourceCategory]:
    mission_context = organization.mission or project.programs or "the mission"
    return [
        ResourceCategory("Technical Assistance", f"Advisory support can help translate {mission_context} into stronger operations, partnerships, and implementation plans."),
        ResourceCategory("Capacity Building Programs", "Capacity programs can strengthen governance, fundraising, evaluation, financial management, and delivery systems."),
        ResourceCategory("Nonprofit Accelerators", "Accelerators can provide coaching, peer learning, pitch support, and structured growth milestones."),
        ResourceCategory("Training & Professional Development", "Training can improve staff skills in program delivery, data, leadership, compliance, and community engagement."),
        ResourceCategory("Volunteer Resources", "Volunteer resources can extend service capacity, mentoring, outreach, events, and administrative support."),
        ResourceCategory("AmeriCorps & National Service Programs", "National service can support direct service roles, community outreach, tutoring, digital navigation, and capacity projects."),
        ResourceCategory("Fellowships", "Fellowships can provide skilled short-term talent for strategy, research, operations, design, or technology work."),
        ResourceCategory("Shared Services", "Shared services can reduce operational burden for finance, HR, legal, data, communications, and back-office needs."),
        ResourceCategory("Software & Technology Resources", "Technology resources can strengthen data collection, outreach, case management, learning, and reporting."),
        ResourceCategory("Equipment & Infrastructure Resources", "Equipment and infrastructure resources can support facilities, devices, connectivity, and program delivery assets."),
    ]


def _recommendations() -> list[ResourceRecommendation]:
    return [
        ResourceRecommendation("Technical Assistance Providers", 92, "High-value support for program design, evaluation, operations, and implementation planning."),
        ResourceRecommendation("Capacity Building Organizations", 90, "Useful for governance, fundraising, finance, leadership, and organizational sustainability."),
        ResourceRecommendation("Nonprofit Support Centers", 86, "Strong fit for training, coaching, templates, nonprofit compliance, and local peer networks."),
        ResourceRecommendation("Volunteer Networks", 84, "Relevant when programs can use mentors, tutors, ambassadors, event help, or operational volunteers."),
        ResourceRecommendation("AmeriCorps Programs", 82, "Useful for direct service, digital navigation, outreach, and capacity-building roles."),
        ResourceRecommendation("University Support Programs", 80, "Relevant for research, fellows, interns, evaluation, clinics, and student project teams."),
        ResourceRecommendation("Software Donation Programs", 78, "Helpful for CRM, productivity, data, learning, cybersecurity, and communications tools."),
        ResourceRecommendation("Shared Service Organizations", 76, "Useful when back-office capacity is limited or expensive to build alone."),
        ResourceRecommendation("Equipment Assistance Programs", 74, "Relevant for devices, furniture, program supplies, facilities, and infrastructure needs."),
        ResourceRecommendation("Broadband & Digital Access Programs", 72, "Relevant when programs include digital skills, online access, technology navigation, or connected devices."),
    ]


def _specific_actions(checklist: list[ResourceChecklistItem]) -> list[str]:
    missing = {item.label for item in checklist if item.status == "Missing"}
    actions = []

    if "Technology Needs" in missing:
        actions.append("Document technology needs, including software, devices, data systems, cybersecurity, and connectivity gaps.")
    if "Volunteer Strategy" in missing:
        actions.append("Create a volunteer engagement strategy with roles, screening needs, onboarding, supervision, and retention steps.")
    if "Capacity Building Strategy" in missing:
        actions.append("Assess capacity-building opportunities across governance, finance, evaluation, leadership, and operations.")
    if "Partnership Inventory" in missing:
        actions.append("Develop a partnership inventory that lists current partners, roles, referrals, and resource gaps.")
    if "Outcomes / Impact" in missing:
        actions.append("Identify training priorities for staff and volunteers based on missing outcome and reporting capabilities.")
    if "Budget Information" in missing:
        actions.append("Create an organizational resource plan that separates funding needs from non-funding supports.")

    actions.append("Identify training priorities for the next two quarters.")
    actions.append("Create an organizational resource plan covering training, technical assistance, volunteers, technology, facilities, equipment, and shared services.")
    return actions[:8]


def build_resource_readiness(project, funding_criteria=None) -> ResourceReadiness:
    organization = project.organization
    score = 35
    strengths = []
    gaps = []

    if organization.mission.strip():
        strengths.append("Mission clarity can guide non-funding resource targeting.")
        score += 9
    else:
        gaps.append("Add a mission statement before resource planning.")

    if project.programs.strip():
        strengths.append("Program definition helps identify training, volunteer, technology, and technical assistance needs.")
        score += 10
    else:
        gaps.append("Define programs before matching resource categories.")

    if organization.city or organization.county or organization.state or organization.service_area_notes:
        strengths.append("Service geography supports local volunteer, university, accelerator, and technical assistance matching.")
        score += 8
    else:
        gaps.append("Add service geography for local resource matching.")

    target_population_ready = _has_values(organization.beneficiaries) or bool(
        funding_criteria and _has_values(funding_criteria.beneficiaries)
    )
    if target_population_ready:
        strengths.append("Target population is clear for resource partners and volunteer programs.")
        score += 8
    else:
        gaps.append("Add beneficiaries or target population language.")

    if _has_values(organization.outcomes_and_impact):
        strengths.append("Outcome evidence can help prioritize technical assistance and training.")
        score += 8
    else:
        gaps.append("Add outcomes or impact evidence to guide capacity-building priorities.")

    if organization.budget_range.strip():
        strengths.append("Budget information helps separate funded needs from in-kind resource needs.")
        score += 7
    else:
        gaps.append("Add budget range or operating-cost context.")

    if _has_values(organization.existing_partnerships):
        strengths.append("Existing partnerships can unlock volunteers, shared services, referrals, and technical assistance.")
        score += 7
    else:
        gaps.append("Add a partnership inventory.")

    if _has_values(organization.current_funding_sources):
        strengths.append("Current funding sources clarify sustainability context for resource planning.")
        score += 5
    else:
        gaps.append("Add current funding sources.")

    score = max(0, min(score, 100))
    checklist = [
        _checklist_item("Mission Clarity", bool(organization.mission.strip()), "Mission is clear enough for resource targeting.", "Add a concise mission statement."),
        _checklist_item("Program Definition", bool(project.programs.strip()), "Programs are defined for resource matching.", "Add program activities and delivery model."),
        _checklist_item("Service Geography", bool(organization.city or organization.county or organization.state or organization.service_area_notes), "Geography is available for local resource mapping.", "Add city, county, state, or service-area notes."),
        _checklist_item("Target Population", target_population_ready, "Target population is clear for partners and volunteer programs.", "Add beneficiaries or target population language."),
        _checklist_item("Outcomes / Impact", _has_values(organization.outcomes_and_impact), "Outcome evidence is available for capacity planning.", "Add outcomes, metrics, or evaluation notes."),
        _checklist_item("Budget Information", bool(organization.budget_range.strip()), "Budget range is available for sustainability planning.", "Add budget range or operating-cost context."),
        _checklist_item("Partnership Inventory", _has_values(organization.existing_partnerships), "Partnership inventory is available.", "List partners, roles, referrals, and support gaps."),
        _checklist_item("Technology Needs", False, "Technology needs are documented.", "Document technology, software, devices, data, and connectivity needs."),
        _checklist_item("Volunteer Strategy", False, "Volunteer strategy is documented.", "Create volunteer roles, onboarding, supervision, and retention plan."),
        _checklist_item("Capacity Building Strategy", False, "Capacity-building strategy is documented.", "Define priority capacity-building needs and target support providers."),
    ]
    return ResourceReadiness(
        readiness_score=score,
        readiness_level=_level(score),
        strengths=strengths,
        gaps=gaps,
        categories=_resource_categories(project, organization),
        recommendations=_recommendations(),
        checklist=checklist,
        actions=_specific_actions(checklist),
        ecosystem_items=RESOURCE_ECOSYSTEM_ITEMS,
    )
