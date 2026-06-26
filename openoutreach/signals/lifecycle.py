from dataclasses import dataclass
from datetime import timedelta

from django.utils import timezone

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

LIFECYCLE_TRANSITIONS = {
    Opportunity.LifecycleStatus.DISCOVERED: [
        (Opportunity.LifecycleStatus.REVIEWING, "Advance Stage"),
    ],
    Opportunity.LifecycleStatus.REVIEWING: [
        (Opportunity.LifecycleStatus.QUALIFIED, "Advance Stage"),
        (Opportunity.LifecycleStatus.DISCOVERED, "Move Back"),
    ],
    Opportunity.LifecycleStatus.QUALIFIED: [
        (Opportunity.LifecycleStatus.PURSUING, "Advance Stage"),
        (Opportunity.LifecycleStatus.REVIEWING, "Move Back"),
    ],
    Opportunity.LifecycleStatus.PURSUING: [
        (Opportunity.LifecycleStatus.APPLICATION_DRAFTING, "Advance Stage"),
    ],
    Opportunity.LifecycleStatus.APPLICATION_DRAFTING: [
        (Opportunity.LifecycleStatus.SUBMITTED, "Advance Stage"),
    ],
    Opportunity.LifecycleStatus.SUBMITTED: [
        (Opportunity.LifecycleStatus.AWARDED, "Mark Awarded"),
        (Opportunity.LifecycleStatus.DECLINED, "Mark Declined"),
    ],
    Opportunity.LifecycleStatus.AWARDED: [
        (Opportunity.LifecycleStatus.CLOSED, "Close"),
    ],
    Opportunity.LifecycleStatus.DECLINED: [
        (Opportunity.LifecycleStatus.CLOSED, "Close"),
    ],
    Opportunity.LifecycleStatus.CLOSED: [],
}


@dataclass(frozen=True)
class LifecycleTransition:
    target_status: str
    target_label: str
    action_label: str


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
class PipelineHealth:
    score: int
    level: str
    active_opportunities: int
    qualified_opportunities: int
    submitted_opportunities: int
    awarded_opportunities: int
    stale_opportunities: int
    overdue_opportunities: int
    upcoming_deadlines: int


@dataclass(frozen=True)
class LifecycleSummary:
    stages: list[LifecycleStage]
    summary_stages: list[LifecycleStage]
    active_opportunities: int
    submitted_opportunities: int
    awarded_opportunities: int
    highest_priority_active_opportunity: Opportunity | None
    health: PipelineHealth

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


def lifecycle_transitions(status: str) -> list[LifecycleTransition]:
    return [
        LifecycleTransition(
            target_status=target_status,
            target_label=Opportunity.LifecycleStatus(target_status).label,
            action_label=action_label,
        )
        for target_status, action_label in LIFECYCLE_TRANSITIONS.get(status, [])
    ]


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


def _pipeline_health(opportunities: list[Opportunity]) -> PipelineHealth:
    now = timezone.now()
    today = now.date()
    active = [
        opportunity
        for opportunity in opportunities
        if opportunity.lifecycle_status in ACTIVE_LIFECYCLE_STATUSES
    ]
    qualified_count = sum(
        1
        for opportunity in opportunities
        if opportunity.lifecycle_status == Opportunity.LifecycleStatus.QUALIFIED
    )
    submitted_count = sum(
        1
        for opportunity in opportunities
        if opportunity.lifecycle_status == Opportunity.LifecycleStatus.SUBMITTED
    )
    awarded_count = sum(
        1
        for opportunity in opportunities
        if opportunity.lifecycle_status == Opportunity.LifecycleStatus.AWARDED
    )
    stale_count = sum(
        1
        for opportunity in active
        if (now - opportunity.updated_at).days >= 30
    )
    overdue_count = sum(
        1
        for opportunity in active
        if opportunity.deadline and opportunity.deadline < today
    )
    upcoming_deadlines = sum(
        1
        for opportunity in active
        if opportunity.deadline and today <= opportunity.deadline <= today + timedelta(days=45)
    )

    score = 45
    if active:
        score += 12
    if qualified_count:
        score += 10
    if submitted_count:
        score += 12
    if awarded_count:
        score += 16
    if upcoming_deadlines:
        score += 5
    score -= min(stale_count * 6, 24)
    score -= min(overdue_count * 10, 30)
    score = max(0, min(score, 100))

    if score >= 85:
        level = "Excellent"
    elif score >= 70:
        level = "Healthy"
    elif score >= 50:
        level = "Needs Attention"
    else:
        level = "At Risk"
    return PipelineHealth(
        score=score,
        level=level,
        active_opportunities=len(active),
        qualified_opportunities=qualified_count,
        submitted_opportunities=submitted_count,
        awarded_opportunities=awarded_count,
        stale_opportunities=stale_count,
        overdue_opportunities=overdue_count,
        upcoming_deadlines=upcoming_deadlines,
    )


def transition_opportunity_lifecycle(opportunity: Opportunity, target_status: str, *, actor=None) -> Opportunity:
    allowed_targets = {
        transition.target_status
        for transition in lifecycle_transitions(opportunity.lifecycle_status)
    }
    if target_status not in allowed_targets:
        return opportunity
    previous_status = opportunity.lifecycle_status
    history = list(opportunity.lifecycle_status_history or [])
    history.append({
        "from": previous_status,
        "to": target_status,
        "actor": getattr(actor, "username", "") if actor else "",
        "updated_at": timezone.now().isoformat(),
    })
    opportunity.lifecycle_status = target_status
    opportunity.lifecycle_status_history = history
    opportunity.save(update_fields=["lifecycle_status", "lifecycle_status_history", "updated_at"])
    return opportunity


def assign_opportunity_owner(opportunity: Opportunity, owner) -> Opportunity:
    opportunity.assigned_owner = owner
    opportunity.save(update_fields=["assigned_owner", "updated_at"])
    return opportunity


def build_lifecycle_summary(project=None, limit_per_stage: int | None = None) -> LifecycleSummary:
    qs = Opportunity.objects.select_related("source_organization", "assigned_owner").order_by("deadline", "name")
    if project is not None:
        qs = qs.filter(project=project)
    opportunities = list(qs)
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
        health=_pipeline_health(opportunities),
    )
