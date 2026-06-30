from dataclasses import dataclass

from openoutreach.funding.models import Opportunity, SourceOrganization
from openoutreach.signals.celebrations import CelebrationOverview, build_celebration_overview
from openoutreach.signals.documents import DocumentEvidenceHealth, build_document_evidence_health
from openoutreach.signals.forecasting import PipelineForecast, build_pipeline_forecast
from openoutreach.signals.lifecycle import LifecycleSummary
from openoutreach.signals.models import OrganizationAnalysisRun
from openoutreach.signals.opportunity_work import OpportunityWorkSummary, build_work_summary
from openoutreach.signals.readiness import (
    OpportunityPursuitSummary,
    ReadinessOverview,
    build_opportunity_pursuit_summary,
    build_readiness_overview,
)
from openoutreach.signals.relationships import RelationshipOverview, build_relationship_overview


@dataclass(frozen=True)
class ExecutiveKpi:
    label: str
    score: int
    level: str
    insight: str
    href_name: str


@dataclass(frozen=True)
class PipelineColumn:
    label: str
    count: int
    opportunities: list[object]


@dataclass(frozen=True)
class ChartBar:
    label: str
    value: int


@dataclass(frozen=True)
class MatchHealth:
    total_matches: int
    excellent_matches: int
    strong_matches: int
    moderate_matches: int
    weak_matches: int


@dataclass(frozen=True)
class DiscoveryHealth:
    total_source_organizations: int
    opportunity_categories: int
    active_opportunities: int
    upcoming_deadlines: list[object]


@dataclass(frozen=True)
class ExecutiveDashboard:
    organization_name: str
    ecosystem_score: int
    ecosystem_level: str
    overall_match_score: int
    last_analysis_date: object | None
    kpis: list[ExecutiveKpi]
    total_opportunities: int
    active_opportunities: int
    high_priority_opportunities: int
    applied_opportunities: int
    won_opportunities: int
    pipeline_columns: list[PipelineColumn]
    match_health: MatchHealth
    discovery_health: DiscoveryHealth
    executive_actions: list[str]
    score_chart: list[ChartBar]
    category_distribution: list[ChartBar]
    status_distribution: list[ChartBar]
    priority_distribution: list[ChartBar]
    lifecycle_summary: LifecycleSummary
    work_summary: OpportunityWorkSummary
    readiness: ReadinessOverview
    pursuit_summary: OpportunityPursuitSummary
    document_evidence_health: DocumentEvidenceHealth
    celebration_overview: CelebrationOverview
    forecast: PipelineForecast
    relationships: RelationshipOverview


def _relevant_upcoming_deadlines(project, limit=5):
    """Upcoming deadlines a client should actually act on — relevant to the org and
    US-eligible (same filters as the Opportunities page, so the dashboard matches)."""
    from openoutreach.funding.relevance import org_keywords, opportunity_relevance, is_off_geography

    keywords = org_keywords(project.organization)
    out, seen_names = [], set()
    qs = (
        Opportunity.objects.filter(project=project)
        .exclude(deadline__isnull=True)
        .exclude(status__in=[Opportunity.Status.EXPIRED, Opportunity.Status.ARCHIVED])
        .order_by("deadline", "name")
    )
    for opp in qs:
        if is_off_geography(opp, project.organization):
            continue
        if opportunity_relevance(opp, keywords) <= 0:
            continue
        key = opp.name.strip().lower()
        if key in seen_names:  # same grant posted under multiple IDs — show once
            continue
        seen_names.add(key)
        out.append(opp)
        if len(out) >= limit:
            break
    return out


def _top_insight(readiness) -> str:
    strengths = getattr(readiness, "strengths", None) or []
    gaps = getattr(readiness, "gaps", None) or []
    if strengths:
        return strengths[0]
    if gaps:
        return gaps[0]
    return "No major signal detected yet."


def _match_health(match_overview) -> MatchHealth:
    matches = [
        match
        for category in match_overview.categories
        for match in category.matches
    ]
    return MatchHealth(
        total_matches=len(matches),
        excellent_matches=sum(1 for match in matches if match.score >= 90),
        strong_matches=sum(1 for match in matches if 75 <= match.score < 90),
        moderate_matches=sum(1 for match in matches if 60 <= match.score < 75),
        weak_matches=sum(1 for match in matches if match.score < 60),
    )


def _pipeline_columns(project) -> list[PipelineColumn]:
    base = Opportunity.objects.filter(project=project)
    discovered_reviewing = base.filter(
        lifecycle_status__in=[
            Opportunity.LifecycleStatus.DISCOVERED,
            Opportunity.LifecycleStatus.REVIEWING,
        ],
    ).order_by("deadline", "name")
    pursuing_qs = base.filter(
        lifecycle_status__in=[
            Opportunity.LifecycleStatus.QUALIFIED,
            Opportunity.LifecycleStatus.PURSUING,
        ],
    ).order_by("deadline", "name")
    drafting_submitted = base.filter(
        lifecycle_status__in=[
            Opportunity.LifecycleStatus.APPLICATION_DRAFTING,
            Opportunity.LifecycleStatus.SUBMITTED,
        ],
    ).order_by("deadline", "name")
    awarded_qs = base.filter(
        lifecycle_status=Opportunity.LifecycleStatus.AWARDED,
    ).order_by("deadline", "name")
    closed_qs = base.filter(
        lifecycle_status__in=[
            Opportunity.LifecycleStatus.DECLINED,
            Opportunity.LifecycleStatus.CLOSED,
        ],
    ).order_by("deadline", "name")
    return [
        PipelineColumn("Exploring", discovered_reviewing.count(), list(discovered_reviewing[:6])),
        PipelineColumn("Pursuing", pursuing_qs.count(), list(pursuing_qs[:6])),
        PipelineColumn("In Progress", drafting_submitted.count(), list(drafting_submitted[:6])),
        PipelineColumn("Awarded", awarded_qs.count(), list(awarded_qs[:6])),
        PipelineColumn("Closed", closed_qs.count(), list(closed_qs[:6])),
    ]


def _distribution(values, choices) -> list[ChartBar]:
    return [
        ChartBar(label=label, value=sum(1 for value in values if value == choice_value))
        for choice_value, label in choices
    ]


def _last_analysis_date(project):
    analysis_run = (
        OrganizationAnalysisRun.objects
        .filter(organization=project.organization)
        .order_by("-completed_at", "-created_at")
        .first()
    )
    if not analysis_run:
        return None
    return analysis_run.completed_at or analysis_run.created_at


def build_executive_dashboard(
    project,
    ecosystem,
    funding_readiness,
    government_readiness,
    resource_readiness,
    partnership_readiness,
    match_overview,
    discovery_overview,
) -> ExecutiveDashboard:
    opportunities = list(Opportunity.objects.filter(project=project))
    actions = list(match_overview.highest_leverage_actions)
    for action in ecosystem.recommended_actions:
        if action not in actions:
            actions.append(action)

    readiness = build_readiness_overview(
        project, funding_readiness, government_readiness, resource_readiness, partnership_readiness,
    )
    pursuit_summary = build_opportunity_pursuit_summary(project)
    document_evidence_health = build_document_evidence_health(project)

    return ExecutiveDashboard(
        organization_name=project.organization.name,
        ecosystem_score=ecosystem.score,
        ecosystem_level=ecosystem.level,
        overall_match_score=match_overview.overall_score,
        last_analysis_date=_last_analysis_date(project),
        kpis=[
            ExecutiveKpi(
                "Funding Score",
                funding_readiness.readiness_score,
                funding_readiness.readiness_level,
                _top_insight(funding_readiness),
                "project-funding",
            ),
            ExecutiveKpi(
                "Government Score",
                government_readiness.readiness_score,
                government_readiness.readiness_level,
                _top_insight(government_readiness),
                "project-government",
            ),
            ExecutiveKpi(
                "Resource Score",
                resource_readiness.readiness_score,
                resource_readiness.readiness_level,
                _top_insight(resource_readiness),
                "project-resources",
            ),
            ExecutiveKpi(
                "Partnership Score",
                partnership_readiness.readiness_score,
                partnership_readiness.readiness_level,
                _top_insight(partnership_readiness),
                "project-partnerships",
            ),
        ],
        total_opportunities=discovery_overview.total_opportunities,
        active_opportunities=discovery_overview.active_opportunities,
        high_priority_opportunities=discovery_overview.high_priority_opportunities,
        applied_opportunities=discovery_overview.applied_opportunities,
        won_opportunities=discovery_overview.won_opportunities,
        pipeline_columns=_pipeline_columns(project),
        match_health=_match_health(match_overview),
        discovery_health=DiscoveryHealth(
            total_source_organizations=SourceOrganization.objects.filter(active=True).count(),
            opportunity_categories=len(discovery_overview.opportunity_types),
            active_opportunities=discovery_overview.active_opportunities,
            upcoming_deadlines=_relevant_upcoming_deadlines(project),
        ),
        executive_actions=actions[:5],
        score_chart=[
            ChartBar("Funding", funding_readiness.readiness_score),
            ChartBar("Government", government_readiness.readiness_score),
            ChartBar("Resources", resource_readiness.readiness_score),
            ChartBar("Partnerships", partnership_readiness.readiness_score),
        ],
        category_distribution=[
            ChartBar(group.label, group.count)
            for group in discovery_overview.groups
        ],
        status_distribution=_distribution([opportunity.lifecycle_status for opportunity in opportunities], Opportunity.LifecycleStatus.choices),
        priority_distribution=_distribution(
            [opportunity.priority_level for opportunity in opportunities],
            Opportunity.PriorityLevel.choices,
        ),
        lifecycle_summary=discovery_overview.lifecycle_summary,
        work_summary=build_work_summary(project),
        readiness=readiness,
        pursuit_summary=pursuit_summary,
        document_evidence_health=document_evidence_health,
        celebration_overview=build_celebration_overview(project),
        forecast=build_pipeline_forecast(project),
        relationships=build_relationship_overview(project),
    )
