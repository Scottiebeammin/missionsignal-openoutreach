from dataclasses import dataclass

from openoutreach.funding.models import Opportunity


LIFECYCLE_ACTIONS = {
    Opportunity.LifecycleStatus.DISCOVERED: "Review eligibility",
    Opportunity.LifecycleStatus.REVIEWING: "Confirm fit and missing requirements",
    Opportunity.LifecycleStatus.QUALIFIED: "Identify program alignment",
    Opportunity.LifecycleStatus.PURSUING: "Assign owner and collect requirements",
    Opportunity.LifecycleStatus.APPLICATION_DRAFTING: "Draft narrative and gather attachments",
    Opportunity.LifecycleStatus.SUBMITTED: "Monitor status and follow up",
    Opportunity.LifecycleStatus.AWARDED: "Prepare implementation plan",
    Opportunity.LifecycleStatus.DECLINED: "Review feedback and archive",
    Opportunity.LifecycleStatus.CLOSED: "Archive notes and preserve lessons learned",
}

PIPELINE_STAGE_VALUES = [
    Opportunity.LifecycleStatus.DISCOVERED,
    Opportunity.LifecycleStatus.REVIEWING,
    Opportunity.LifecycleStatus.QUALIFIED,
    Opportunity.LifecycleStatus.PURSUING,
    Opportunity.LifecycleStatus.APPLICATION_DRAFTING,
    Opportunity.LifecycleStatus.SUBMITTED,
    Opportunity.LifecycleStatus.AWARDED,
    Opportunity.LifecycleStatus.DECLINED,
    Opportunity.LifecycleStatus.CLOSED,
]

SUMMARY_STAGE_VALUES = [
    Opportunity.LifecycleStatus.DISCOVERED,
    Opportunity.LifecycleStatus.QUALIFIED,
    Opportunity.LifecycleStatus.PURSUING,
    Opportunity.LifecycleStatus.SUBMITTED,
    Opportunity.LifecycleStatus.AWARDED,
]

ACTIVE_LIFECYCLE_STATUSES = {
    Opportunity.LifecycleStatus.DISCOVERED,
    Opportunity.LifecycleStatus.REVIEWING,
    Opportunity.LifecycleStatus.QUALIFIED,
    Opportunity.LifecycleStatus.PURSUING,
    Opportunity.LifecycleStatus.APPLICATION_DRAFTING,
    Opportunity.LifecycleStatus.SUBMITTED,
}


@dataclass(frozen=True)
class LifecycleStage:
    value: str
    label: str
    count: int
    opportunities: list[Opportunity]
    recommended_next_step: str


@dataclass(frozen=True)
class LifecycleSummary:
    stages: list[LifecycleStage]
    summary_stages: list[LifecycleStage]
    active_opportunities: int
    submitted_opportunities: int
    awarded_opportunities: int

    @property
    def highest_activity_stage(self) -> str:
        if not self.stages:
            return "No lifecycle activity"
        stage = sorted(self.stages, key=lambda item: (-item.count, item.label))[0]
        return stage.label if stage.count else "No lifecycle activity"


def recommended_lifecycle_action(status: str) -> str:
    return LIFECYCLE_ACTIONS.get(status, "Review eligibility")


def suggested_lifecycle_stage() -> str:
    return Opportunity.LifecycleStatus.DISCOVERED.label


def build_lifecycle_summary(limit_per_stage: int | None = None) -> LifecycleSummary:
    opportunities = list(
        Opportunity.objects.select_related("source_organization", "assigned_owner")
        .order_by("deadline", "name")
    )
    stages = []
    for value in PIPELINE_STAGE_VALUES:
        stage_opportunities = [
            opportunity
            for opportunity in opportunities
            if opportunity.lifecycle_status == value
        ]
        stages.append(
            LifecycleStage(
                value=value,
                label=Opportunity.LifecycleStatus(value).label,
                count=len(stage_opportunities),
                opportunities=stage_opportunities[:limit_per_stage] if limit_per_stage else stage_opportunities,
                recommended_next_step=recommended_lifecycle_action(value),
            )
        )
    summary_stages = [
        stage
        for stage in stages
        if stage.value in SUMMARY_STAGE_VALUES
    ]
    return LifecycleSummary(
        stages=stages,
        summary_stages=summary_stages,
        active_opportunities=sum(
            1
            for opportunity in opportunities
            if opportunity.lifecycle_status in ACTIVE_LIFECYCLE_STATUSES
        ),
        submitted_opportunities=sum(
            1
            for opportunity in opportunities
            if opportunity.lifecycle_status == Opportunity.LifecycleStatus.SUBMITTED
        ),
        awarded_opportunities=sum(
            1
            for opportunity in opportunities
            if opportunity.lifecycle_status == Opportunity.LifecycleStatus.AWARDED
        ),
    )
