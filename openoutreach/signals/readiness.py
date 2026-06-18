from dataclasses import dataclass

from django.utils import timezone

from openoutreach.funding.models import Opportunity, OpportunityDeadline, OpportunityTask


@dataclass(frozen=True)
class CompletenessArea:
    label: str
    complete: bool
    detail: str


@dataclass(frozen=True)
class OrganizationCompleteness:
    score: int
    level: str
    completed_areas: list[str]
    missing_areas: list[str]
    highest_leverage_missing_area: str
    areas: list[CompletenessArea]


@dataclass(frozen=True)
class ReadinessDimension:
    label: str
    score: int
    level: str
    insight: str


@dataclass(frozen=True)
class ReadinessOverview:
    overall_score: int
    level: str
    strengths: list[str]
    gaps: list[str]
    recommended_actions: list[str]
    organization_completeness: OrganizationCompleteness
    dimensions: list[ReadinessDimension]


@dataclass(frozen=True)
class OpportunityPursuitReadiness:
    score: int
    level: str
    why_ready: list[str]
    why_not_ready: list[str]
    highest_leverage_improvement: str
    missing_areas: list[str]


@dataclass(frozen=True)
class OpportunityPursuitSummary:
    average_score: int
    ready_opportunities: int
    needs_preparation_opportunities: int
    strongest_opportunity: Opportunity | None
    weakest_opportunity: Opportunity | None


def _has_text(value) -> bool:
    return bool(str(value or "").strip())


def _has_values(values) -> bool:
    if isinstance(values, str):
        return _has_text(values)
    return any(_has_text(value) for value in values or [])


def _completeness_level(score: int) -> str:
    if score >= 90:
        return "Advanced"
    if score >= 78:
        return "Complete"
    if score >= 60:
        return "Developing"
    if score >= 40:
        return "Emerging"
    return "Incomplete"


def _readiness_level(score: int) -> str:
    if score >= 85:
        return "Advanced"
    if score >= 70:
        return "Competitive"
    if score >= 50:
        return "Developing"
    return "Emerging"


def _pursuit_level(score: int) -> str:
    if score >= 85:
        return "Strong Candidate"
    if score >= 70:
        return "Ready"
    if score >= 50:
        return "Needs Preparation"
    return "Not Ready"


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


def build_organization_completeness(project, module_readiness: dict | None = None) -> OrganizationCompleteness:
    organization = project.organization
    module_readiness = module_readiness or {}
    funding_score = getattr(module_readiness.get("funding"), "readiness_score", 0)
    government_score = getattr(module_readiness.get("government"), "readiness_score", 0)
    resource_score = getattr(module_readiness.get("resource"), "readiness_score", 0)

    areas = [
        CompletenessArea("Mission", _has_text(organization.mission), "Mission statement is present."),
        CompletenessArea("Programs", _has_text(project.programs), "Program model is defined."),
        CompletenessArea("Beneficiaries", _has_values(organization.beneficiaries), "Target population is identified."),
        CompletenessArea(
            "Geography",
            _has_text(organization.city)
            or _has_text(organization.county)
            or _has_text(organization.state)
            or _has_values(organization.service_geographies)
            or _has_text(organization.service_area_notes),
            "Service geography is defined.",
        ),
        CompletenessArea("Outcomes", _has_values(organization.outcomes_and_impact), "Outcomes and impact evidence are documented."),
        CompletenessArea("Organization Type", _has_values(organization.organization_type), "Organization type is documented."),
        CompletenessArea("Partnerships", _has_values(organization.existing_partnerships), "Existing partnerships are documented."),
        CompletenessArea("Resource Capacity", resource_score >= 65 or _has_values(organization.capabilities), "Capacity and resources are documented."),
        CompletenessArea("Funding Readiness", funding_score >= 65, "Funding readiness is strong enough for pursuit planning."),
        CompletenessArea("Government Readiness", government_score >= 65, "Government readiness is strong enough for public-sector pursuit."),
    ]
    completed = [area.label for area in areas if area.complete]
    missing = [area.label for area in areas if not area.complete]
    score = round((len(completed) / len(areas)) * 100) if areas else 0
    leverage_order = [
        "Outcomes",
        "Budget",
        "Partnerships",
        "Funding Readiness",
        "Government Readiness",
        "Resource Capacity",
        "Beneficiaries",
        "Geography",
        "Programs",
        "Mission",
        "Organization Type",
    ]
    highest = next((label for label in leverage_order if label in missing), "No missing area detected")
    return OrganizationCompleteness(
        score=score,
        level=_completeness_level(score),
        completed_areas=completed,
        missing_areas=missing,
        highest_leverage_missing_area=highest,
        areas=areas,
    )


def _dimension(label: str, score: int, positive: str, gap: str) -> ReadinessDimension:
    return ReadinessDimension(
        label=label,
        score=max(0, min(score, 100)),
        level=_readiness_level(score),
        insight=positive if score >= 70 else gap,
    )


def build_readiness_overview(
    project,
    funding_readiness,
    government_readiness,
    resource_readiness,
    partnership_readiness,
) -> ReadinessOverview:
    organization = project.organization
    completeness = build_organization_completeness(
        project,
        {
            "funding": funding_readiness,
            "government": government_readiness,
            "resource": resource_readiness,
            "partnership": partnership_readiness,
        },
    )
    mission_score = 90 if _has_text(organization.mission) else 20
    program_score = 90 if _has_text(project.programs) else 25
    outcome_score = 88 if _has_values(organization.outcomes_and_impact) else 35
    operational_score = round(
        (
            (90 if _has_text(organization.budget_range) else 45)
            + (85 if _has_values(organization.current_funding_sources) else 45)
            + (85 if _has_values(organization.existing_partnerships) else 45)
            + completeness.score
        )
        / 4
    )
    dimensions = [
        _dimension("Mission Readiness", mission_score, "Mission is clear enough to anchor opportunity work.", "Mission needs clearer positioning."),
        _dimension("Program Readiness", program_score, "Programs are defined for opportunity alignment.", "Programs need clearer definition."),
        _dimension("Outcome Readiness", outcome_score, "Outcomes can support credibility.", "Outcomes evidence is missing or thin."),
        _dimension("Funding Readiness", funding_readiness.readiness_score, "Funding lane is usable now.", "Funding readiness needs stronger materials."),
        _dimension("Government Readiness", government_readiness.readiness_score, "Government lane is usable now.", "Government engagement needs preparation."),
        _dimension("Partnership Readiness", partnership_readiness.readiness_score, "Partnership lane supports credibility.", "Partnership evidence needs work."),
        _dimension("Resource Readiness", resource_readiness.readiness_score, "Resource lane can support capacity.", "Resource capacity needs definition."),
        _dimension("Operational Readiness", operational_score, "Operations are ready for active pursuit.", "Operational details need cleanup."),
    ]
    overall_score = round(sum(item.score for item in dimensions) / len(dimensions))
    strengths = _dedupe(
        [item.insight for item in dimensions if item.score >= 70]
        + [f"{area} complete" for area in completeness.completed_areas],
        8,
    )
    gaps = _dedupe(
        [item.insight for item in dimensions if item.score < 70]
        + [f"{area} missing" for area in completeness.missing_areas],
        8,
    )
    actions = []
    if "Outcomes" in completeness.missing_areas:
        actions.append("Add measurable outcomes and impact evidence.")
    if not _has_text(organization.budget_range):
        actions.append("Document budget range and budget assumptions.")
    if not _has_values(organization.current_funding_sources):
        actions.append("Add funding sources or funding history.")
    if "Partnerships" in completeness.missing_areas:
        actions.append("Build a partnership inventory.")
    if "Resource Capacity" in completeness.missing_areas:
        actions.append("Create a capacity and resource needs inventory.")
    if "Government Readiness" in completeness.missing_areas:
        actions.append("Build a local government contact strategy.")
    actions.append("Use the readiness dashboard to prioritize the next opportunity preparation sprint.")
    return ReadinessOverview(
        overall_score=overall_score,
        level=_readiness_level(overall_score),
        strengths=strengths,
        gaps=gaps,
        recommended_actions=_dedupe(actions, 7),
        organization_completeness=completeness,
        dimensions=dimensions,
    )


def build_opportunity_pursuit_readiness(project, opportunity: Opportunity) -> OpportunityPursuitReadiness:
    organization = project.organization
    completeness = build_organization_completeness(project)
    tasks = list(opportunity.tasks.all())
    deadlines = list(opportunity.deadlines.all())
    required_documents_ready = any(task.status == OpportunityTask.Status.COMPLETE for task in tasks) or bool(tasks)
    outcomes_ready = _has_values(organization.outcomes_and_impact)
    budget_ready = _has_text(organization.budget_range)
    capacity_ready = _has_values(organization.capabilities) or any(
        task.title.casefold().find("collect required documents") >= 0
        for task in tasks
    )
    partnership_ready = _has_values(organization.existing_partnerships)
    resource_ready = _has_values(organization.capabilities)
    deadline_ready = not any(
        deadline.deadline_date < timezone.localdate()
        and deadline.status != OpportunityDeadline.Status.COMPLETE
        for deadline in deadlines
    )
    factors = [
        (completeness.score, "Organization profile is complete enough for pursuit.", "Organization completeness needs work."),
        (85 if required_documents_ready else 45, "Required document workflow exists.", "Required documents are not yet tracked."),
        (90 if outcomes_ready else 35, "Outcomes evidence is available.", "Outcomes evidence is missing."),
        (88 if budget_ready else 40, "Budget readiness is documented.", "Budget range is not provided."),
        (82 if capacity_ready else 45, "Capacity readiness is visible.", "Capacity readiness needs definition."),
        (85 if partnership_ready else 45, "Partnership evidence is available.", "Partnership inventory is missing."),
        (82 if resource_ready else 45, "Resource capacity is documented.", "Resource readiness needs definition."),
        (88 if deadline_ready else 30, "Deadline status is manageable.", "One or more deadlines are overdue."),
    ]
    score = round(sum(value for value, _ready, _not_ready in factors) / len(factors))
    why_ready = [ready for value, ready, _not_ready in factors if value >= 70]
    why_not_ready = [not_ready for value, _ready, not_ready in factors if value < 70]
    improvement_order = [
        ("Outcomes evidence is missing.", "Add measurable outcomes."),
        ("Budget range is not provided.", "Add annual budget range and budget assumptions."),
        ("Partnership inventory is missing.", "Document partner organizations and relationship history."),
        ("Required documents are not yet tracked.", "Create a required-document checklist."),
        ("Capacity readiness needs definition.", "Document capacity and staffing needs."),
        ("Resource readiness needs definition.", "Create a resource needs inventory."),
        ("One or more deadlines are overdue.", "Resolve overdue deadlines."),
        ("Organization completeness needs work.", "Complete missing organization profile areas."),
    ]
    highest = next(
        (action for missing, action in improvement_order if missing in why_not_ready),
        "Maintain current readiness and confirm pursuit owner.",
    )
    return OpportunityPursuitReadiness(
        score=max(0, min(score, 100)),
        level=_pursuit_level(score),
        why_ready=_dedupe(why_ready, 6),
        why_not_ready=_dedupe(why_not_ready, 6),
        highest_leverage_improvement=highest,
        missing_areas=[missing.replace(".", "") for missing in why_not_ready],
    )


def build_opportunity_pursuit_summary(project) -> OpportunityPursuitSummary:
    opportunities = list(Opportunity.objects.all().order_by("name"))
    readiness = [
        (opportunity, build_opportunity_pursuit_readiness(project, opportunity))
        for opportunity in opportunities
    ]
    if not readiness:
        return OpportunityPursuitSummary(0, 0, 0, None, None)
    average = round(sum(item.score for _opportunity, item in readiness) / len(readiness))
    strongest = sorted(readiness, key=lambda item: (-item[1].score, item[0].name))[0][0]
    weakest = sorted(readiness, key=lambda item: (item[1].score, item[0].name))[0][0]
    return OpportunityPursuitSummary(
        average_score=average,
        ready_opportunities=sum(1 for _opportunity, item in readiness if item.score >= 70),
        needs_preparation_opportunities=sum(1 for _opportunity, item in readiness if item.score < 70),
        strongest_opportunity=strongest,
        weakest_opportunity=weakest,
    )
