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

LIFECYCLE_DESCRIPTIONS = {
    Opportunity.LifecycleStatus.DISCOVERED: "New inventory that needs basic fit review.",
    Opportunity.LifecycleStatus.REVIEWING: "Eligibility, fit, and requirements are being checked.",
    Opportunity.LifecycleStatus.QUALIFIED: "Good-fit opportunities ready for a pursue/no-pursue decision.",
    Opportunity.LifecycleStatus.PURSUING: "Active opportunities with owners, requirements, and deadlines.",
    Opportunity.LifecycleStatus.APPLICATION_DRAFTING: "Narrative, attachments, outcomes, and budget details are being assembled.",
    Opportunity.LifecycleStatus.SUBMITTED: "Submitted opportunities that need follow-up and status tracking.",
    Opportunity.LifecycleStatus.AWARDED: "Won opportunities ready for implementation and reporting setup.",
    Opportunity.LifecycleStatus.DECLINED: "Declined opportunities to review before archiving.",
    Opportunity.LifecycleStatus.CLOSED: "Completed or archived opportunities with lessons preserved.",
}

LIFECYCLE_ACTION_LISTS = {
    Opportunity.LifecycleStatus.DISCOVERED: [
        "Review eligibility.",
        "Check geography fit.",
        "Confirm program alignment.",
    ],
    Opportunity.LifecycleStatus.REVIEWING: [
        "Compare requirements to current profile.",
        "Identify missing documents.",
    ],
    Opportunity.LifecycleStatus.QUALIFIED: [
        "Decide whether to pursue.",
        "Assign internal owner.",
    ],
    Opportunity.LifecycleStatus.PURSUING: [
        "Collect attachments.",
        "Confirm deadlines.",
    ],
    Opportunity.LifecycleStatus.APPLICATION_DRAFTING: [
        "Draft narrative.",
        "Gather outcomes and budget details.",
    ],
    Opportunity.LifecycleStatus.SUBMITTED: [
        "Track follow-up date.",
        "Monitor status.",
    ],
    Opportunity.LifecycleStatus.AWARDED: [
        "Prepare implementation plan.",
        "Track reporting requirements.",
    ],
    Opportunity.LifecycleStatus.DECLINED: [
        "Review feedback.",
        "Save notes for future opportunities.",
    ],
    Opportunity.LifecycleStatus.CLOSED: [
        "Archive lessons learned.",
    ],
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
    description: str
    recommended_actions: list[str]


@dataclass(frozen=True)
class LifecycleSummary:
    stages: list[LifecycleStage]
    summary_stages: list[LifecycleStage]
    active_opportunities: int
    submitted_opportunities: int
    awarded_opportunities: int
    highest_priority_active_opportunity: Opportunity | None

    @property
    def highest_activity_stage(self) -> str:
        if not self.stages:
            return "No lifecycle activity"
        stage = sorted(self.stages, key=lambda item: (-item.count, item.label))[0]
        return stage.label if stage.count else "No lifecycle activity"


def recommended_lifecycle_action(status: str) -> str:
    return LIFECYCLE_ACTIONS.get(status, "Review eligibility")


def lifecycle_description(status: str) -> str:
    return LIFECYCLE_DESCRIPTIONS.get(status, "Manage opportunity progress.")


def lifecycle_actions(status: str) -> list[str]:
    return LIFECYCLE_ACTION_LISTS.get(status, ["Review eligibility."])


def suggested_lifecycle_stage() -> str:
    return Opportunity.LifecycleStatus.DISCOVERED.label


def _highest_priority_active_opportunity(opportunities: list[Opportunity]) -> Opportunity | None:
    priority_rank = {
        Opportunity.PriorityLevel.HIGH: 0,
        Opportunity.PriorityLevel.MEDIUM: 1,
        Opportunity.PriorityLevel.LOW: 2,
    }
    active = [
        opportunity
        for opportunity in opportunities
        if opportunity.lifecycle_status in ACTIVE_LIFECYCLE_STATUSES
    ]
    if not active:
        return None
    return sorted(
        active,
        key=lambda opportunity: (
            priority_rank.get(opportunity.priority_level, 99),
            opportunity.deadline is None,
            opportunity.deadline,
            opportunity.name,
        ),
    )[0]


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
                description=lifecycle_description(value),
                recommended_actions=lifecycle_actions(value),
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
        highest_priority_active_opportunity=_highest_priority_active_opportunity(opportunities),
    )
