from dataclasses import dataclass

from openoutreach.funding.models import (
    DocumentVaultItem,
    EvidenceLibraryItem,
    Opportunity,
    OpportunityDeadline,
    OpportunityTask,
    SourceOrganization,
)
from openoutreach.signals.documents import DocumentEvidenceHealth, build_document_evidence_health
from openoutreach.signals.lifecycle import LifecycleSummary
from openoutreach.signals.models import OrganizationAnalysisRun
from openoutreach.signals.opportunity_work import OpportunityWorkSummary, build_work_summary
from openoutreach.signals.readiness import (
    OpportunityPursuitSummary,
    ReadinessOverview,
    build_opportunity_pursuit_summary,
    build_readiness_overview,
)


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
class CelebrationArea:
    recent_wins: list[str]
    milestones: list[str]
    progress_highlights: list[str]


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
    celebration: CelebrationArea


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


def _pipeline_columns() -> list[PipelineColumn]:
    monitoring_queryset = Opportunity.objects.filter(status=Opportunity.Status.MONITORING).order_by("deadline", "name")
    interested_queryset = Opportunity.objects.filter(
        status__in=[Opportunity.Status.ACTIVE, Opportunity.Status.UPCOMING],
    ).order_by("deadline", "name")
    applied_queryset = Opportunity.objects.filter(status=Opportunity.Status.APPLIED).order_by("deadline", "name")
    won_queryset = Opportunity.objects.filter(status=Opportunity.Status.WON).order_by("deadline", "name")
    archived_queryset = Opportunity.objects.filter(status=Opportunity.Status.ARCHIVED).order_by("deadline", "name")
    return [
        PipelineColumn("Monitoring", monitoring_queryset.count(), list(monitoring_queryset[:6])),
        PipelineColumn("Interested", interested_queryset.count(), list(interested_queryset[:6])),
        PipelineColumn("Applied", applied_queryset.count(), list(applied_queryset[:6])),
        PipelineColumn("Won", won_queryset.count(), list(won_queryset[:6])),
        PipelineColumn("Archived", archived_queryset.count(), list(archived_queryset[:6])),
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


def _pluralize(count: int, singular: str, plural: str | None = None) -> str:
    label = singular if count == 1 else (plural or f"{singular}s")
    return f"{count} {label}"


def _build_celebration_area(
    project, discovery_overview, readiness, pursuit_summary, document_evidence_health,
) -> CelebrationArea:
    active_pipeline_count = discovery_overview.lifecycle_summary.active_opportunities
    submitted_count = discovery_overview.lifecycle_summary.submitted_opportunities
    awarded_count = discovery_overview.lifecycle_summary.awarded_opportunities
    completed_tasks = OpportunityTask.objects.filter(status=OpportunityTask.Status.COMPLETE).count()
    completed_deadlines = OpportunityDeadline.objects.filter(status=OpportunityDeadline.Status.COMPLETE).count()
    available_documents = DocumentVaultItem.objects.filter(
        project=project, status=DocumentVaultItem.Status.AVAILABLE,
    ).count()
    available_evidence = EvidenceLibraryItem.objects.filter(
        project=project, status=EvidenceLibraryItem.Status.AVAILABLE,
    ).count()

    recent_wins = []
    if active_pipeline_count:
        recent_wins.append(
            f"{_pluralize(active_pipeline_count, 'opportunity', 'opportunities')} active in your opportunity web."
        )
    if completed_tasks:
        recent_wins.append(f"{_pluralize(completed_tasks, 'task')} completed across pursuit work.")
    if completed_deadlines:
        recent_wins.append(f"{_pluralize(completed_deadlines, 'deadline')} completed and no longer blocking progress.")
    if available_documents:
        recent_wins.append(f"{_pluralize(available_documents, 'document')} ready in the vault.")
    if available_evidence:
        recent_wins.append(
            f"{_pluralize(available_evidence, 'evidence item', 'evidence items')} added to your opportunity web."
        )
    if submitted_count:
        recent_wins.append(f"{_pluralize(submitted_count, 'opportunity', 'opportunities')} submitted.")
    if awarded_count:
        recent_wins.append(f"{_pluralize(awarded_count, 'opportunity', 'opportunities')} awarded.")
    if not recent_wins:
        recent_wins.append("Your opportunity web is mapped and ready for the next focused action.")

    milestones = [
        f"{project.organization.name} has an Opportunity Web Snapshot in progress.",
        f"{_pluralize(discovery_overview.total_opportunities, 'opportunity', 'opportunities')} mapped across funders, partners, resources, and public-sector lanes.",
    ]
    if discovery_overview.high_priority_opportunities:
        milestones.append(f"{_pluralize(discovery_overview.high_priority_opportunities, 'high-priority opportunity', 'high-priority opportunities')} identified for leadership review.")
    if readiness.organization_completeness.score >= 70:
        milestones.append("Organization completeness is strong enough to support sharper opportunity decisions.")
    if document_evidence_health.document_summary.readiness_score >= 70:
        milestones.append("Document readiness is moving from preparation into pursuit support.")

    progress_highlights = [
        f"Readiness score is {readiness.overall_score}, giving the team a clear baseline for action.",
        f"Average pursuit readiness is {pursuit_summary.average_score} across mapped opportunities.",
    ]
    if discovery_overview.upcoming_opportunities:
        progress_highlights.append(f"{_pluralize(discovery_overview.upcoming_opportunities, 'upcoming opportunity', 'upcoming opportunities')} ready for review.")
    available_evidence_items = (
        document_evidence_health.evidence_summary.total_evidence_items
        - document_evidence_health.evidence_summary.missing_items
    )
    if available_evidence_items:
        progress_highlights.append("Outcome evidence is available to strengthen future narratives.")
    if not progress_highlights:
        progress_highlights.append("Progress will appear here as opportunities, documents, evidence, tasks, and deadlines move forward.")

    return CelebrationArea(
        recent_wins=recent_wins[:5],
        milestones=milestones[:5],
        progress_highlights=progress_highlights[:5],
    )


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
    opportunities = list(Opportunity.objects.all())
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
        pipeline_columns=_pipeline_columns(),
        match_health=_match_health(match_overview),
        discovery_health=DiscoveryHealth(
            total_source_organizations=SourceOrganization.objects.filter(active=True).count(),
            opportunity_categories=len(discovery_overview.opportunity_types),
            active_opportunities=discovery_overview.active_opportunities,
            upcoming_deadlines=list(
                Opportunity.objects.exclude(deadline__isnull=True).order_by("deadline", "name")[:5]
            ),
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
        status_distribution=_distribution([opportunity.status for opportunity in opportunities], Opportunity.Status.choices),
        priority_distribution=_distribution(
            [opportunity.priority_level for opportunity in opportunities],
            Opportunity.PriorityLevel.choices,
        ),
        lifecycle_summary=discovery_overview.lifecycle_summary,
        work_summary=build_work_summary(),
        readiness=readiness,
        pursuit_summary=pursuit_summary,
        document_evidence_health=document_evidence_health,
        celebration=_build_celebration_area(
            project, discovery_overview, readiness, pursuit_summary, document_evidence_health,
        ),
    )
