from dataclasses import dataclass

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
class DiscoveryOverview:
    total_opportunities: int
    active_opportunities: int
    opportunity_types: list[str]
    geography_coverage: list[str]
    groups: list[DiscoveryGroup]
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
    opportunities = list(Opportunity.objects.order_by("name"))
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

    return DiscoveryOverview(
        total_opportunities=len(opportunities),
        active_opportunities=sum(
            1
            for opportunity in opportunities
            if opportunity.status == Opportunity.Status.ACTIVE
        ),
        opportunity_types=opportunity_types,
        geography_coverage=geography_coverage,
        groups=groups,
        top_opportunities=items[:5],
    )
