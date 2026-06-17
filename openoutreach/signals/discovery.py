from dataclasses import dataclass

from django.db.models import Count

from openoutreach.funding.models import Opportunity
from openoutreach.signals.matching import OpportunityMatch, score_inventory_opportunity


@dataclass(frozen=True)
class DiscoveryOpportunity:
    opportunity: Opportunity
    match: OpportunityMatch


@dataclass(frozen=True)
class DiscoveryGroup:
    label: str
    opportunities: list[DiscoveryOpportunity]

    @property
    def count(self) -> int:
        return len(self.opportunities)


@dataclass(frozen=True)
class DiscoveryBreakdown:
    label: str
    count: int


@dataclass(frozen=True)
class DiscoveryOverview:
    total_opportunities: int
    active_opportunities: int
    upcoming_opportunities: int
    monitoring_opportunities: int
    applied_opportunities: int
    won_opportunities: int
    high_priority_opportunities: int
    opportunity_types: list[str]
    geography_coverage: list[str]
    groups: list[DiscoveryGroup]
    priority_groups: list[DiscoveryGroup]
    top_source_organizations: list[DiscoveryBreakdown]
    status_breakdown: list[DiscoveryBreakdown]
    top_opportunities: list[DiscoveryOpportunity]

    @property
    def best_opportunity_category(self) -> str:
        scored_groups = [
            group
            for group in self.groups
            if group.opportunities
        ]
        if not scored_groups:
            return "No opportunities yet"
        best = sorted(
            scored_groups,
            key=lambda group: (
                -max(item.match.score for item in group.opportunities),
                -group.count,
                group.label,
            ),
        )[0]
        return best.label

    @property
    def top_source_organization(self) -> str:
        if not self.top_source_organizations:
            return "No source organizations yet"
        return self.top_source_organizations[0].label


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


def _group_label(opportunity: Opportunity) -> str:
    if opportunity.opportunity_type == Opportunity.OpportunityType.GRANT:
        return "Grants"
    if (
        opportunity.source_type == Opportunity.SourceType.GOVERNMENT
        or opportunity.opportunity_type == Opportunity.OpportunityType.CONTRACT
    ):
        return "Government"
    if opportunity.opportunity_type in {
        Opportunity.OpportunityType.RESOURCE,
        Opportunity.OpportunityType.TRAINING,
        Opportunity.OpportunityType.CAPACITY_BUILDING,
    }:
        return "Resources"
    if opportunity.opportunity_type in {
        Opportunity.OpportunityType.PARTNERSHIP,
        Opportunity.OpportunityType.SPONSORSHIP,
    }:
        return "Partnerships"
    return "Resources"


def build_discovery_overview(project, funding_criteria=None) -> DiscoveryOverview:
    queryset = Opportunity.objects.select_related("source_organization").order_by("name")
    opportunities = list(queryset)
    items = [
        DiscoveryOpportunity(
            opportunity=opportunity,
            match=score_inventory_opportunity(project, opportunity, funding_criteria),
        )
        for opportunity in opportunities
    ]
    items = sorted(
        items,
        key=lambda item: (-item.match.score, item.opportunity.get_opportunity_type_display(), item.opportunity.name),
    )

    groups = []
    for label in ["Grants", "Government", "Resources", "Partnerships"]:
        groups.append(
            DiscoveryGroup(
                label=label,
                opportunities=[item for item in items if _group_label(item.opportunity) == label],
            )
        )

    priority_groups = [
        DiscoveryGroup(
            "High Priority",
            [
                item
                for item in items
                if item.opportunity.priority_level == Opportunity.PriorityLevel.HIGH
            ],
        ),
        DiscoveryGroup(
            "Medium Priority",
            [
                item
                for item in items
                if item.opportunity.priority_level == Opportunity.PriorityLevel.MEDIUM
            ],
        ),
        DiscoveryGroup(
            "Low Priority",
            [
                item
                for item in items
                if item.opportunity.priority_level == Opportunity.PriorityLevel.LOW
            ],
        ),
    ]

    opportunity_types = _dedupe(
        [
            opportunity.get_opportunity_type_display()
            for opportunity in opportunities
        ],
        12,
    )
    geography_coverage = _dedupe(
        [
            geography
            for opportunity in opportunities
            for geography in opportunity.geography
        ],
        12,
    )
    top_source_organizations = [
        DiscoveryBreakdown(
            label=row["source_organization__name"] or row["source_name"] or "Manual",
            count=row["count"],
        )
        for row in Opportunity.objects.values("source_organization__name", "source_name")
        .annotate(count=Count("id"))
        .order_by("-count", "source_organization__name", "source_name")[:5]
    ]
    status_counts = {
        row["status"]: row["count"]
        for row in Opportunity.objects.values("status").annotate(count=Count("id"))
    }
    status_breakdown = [
        DiscoveryBreakdown(label=label, count=status_counts.get(value, 0))
        for value, label in Opportunity.Status.choices
    ]

    return DiscoveryOverview(
        total_opportunities=len(opportunities),
        active_opportunities=sum(
            1
            for opportunity in opportunities
            if opportunity.status == Opportunity.Status.ACTIVE
        ),
        upcoming_opportunities=sum(1 for opportunity in opportunities if opportunity.status == Opportunity.Status.UPCOMING),
        monitoring_opportunities=sum(
            1 for opportunity in opportunities if opportunity.status == Opportunity.Status.MONITORING
        ),
        applied_opportunities=sum(1 for opportunity in opportunities if opportunity.status == Opportunity.Status.APPLIED),
        won_opportunities=sum(1 for opportunity in opportunities if opportunity.status == Opportunity.Status.WON),
        high_priority_opportunities=sum(
            1 for opportunity in opportunities if opportunity.priority_level == Opportunity.PriorityLevel.HIGH
        ),
        opportunity_types=opportunity_types,
        geography_coverage=geography_coverage,
        groups=groups,
        priority_groups=priority_groups,
        top_source_organizations=top_source_organizations,
        status_breakdown=status_breakdown,
        top_opportunities=items[:5],
    )
