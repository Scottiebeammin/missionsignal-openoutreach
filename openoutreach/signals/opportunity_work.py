from dataclasses import dataclass
from datetime import timedelta

from django.utils import timezone

from openoutreach.funding.models import Opportunity, OpportunityDeadline, OpportunityTask
from openoutreach.signals.forecasting import OpportunityForecastContribution, forecast_contribution
from openoutreach.signals.lifecycle import recommended_lifecycle_action
from openoutreach.signals.matching import OpportunityMatch, score_inventory_opportunity


DEFAULT_TASKS_BY_STAGE = {
    Opportunity.LifecycleStatus.DISCOVERED: [
        ("Review eligibility", "Confirm that basic applicant and program requirements are a fit.", OpportunityTask.Priority.HIGH),
        ("Confirm geography fit", "Verify that the opportunity serves the organization's geography.", OpportunityTask.Priority.MEDIUM),
        ("Confirm program alignment", "Check whether current programs map clearly to the opportunity.", OpportunityTask.Priority.MEDIUM),
    ],
    Opportunity.LifecycleStatus.REVIEWING: [
        ("Compare requirements to current profile", "Identify missing documents, data, and eligibility details.", OpportunityTask.Priority.HIGH),
        ("Identify missing documents", "List attachments or records needed before qualification.", OpportunityTask.Priority.MEDIUM),
    ],
    Opportunity.LifecycleStatus.QUALIFIED: [
        ("Decide pursue / no pursue", "Make a clear pursuit decision before work expands.", OpportunityTask.Priority.HIGH),
        ("Assign owner", "Name the person responsible for next steps.", OpportunityTask.Priority.HIGH),
        ("Gather opportunity requirements", "Create a requirements checklist for the opportunity.", OpportunityTask.Priority.MEDIUM),
    ],
    Opportunity.LifecycleStatus.PURSUING: [
        ("Collect required documents", "Gather documents, registrations, and attachments.", OpportunityTask.Priority.HIGH),
        ("Prepare budget details", "Draft the budget inputs needed for the opportunity.", OpportunityTask.Priority.HIGH),
        ("Gather outcome evidence", "Compile outcomes, impact data, and program evidence.", OpportunityTask.Priority.MEDIUM),
    ],
    Opportunity.LifecycleStatus.APPLICATION_DRAFTING: [
        ("Draft narrative", "Prepare the core application or proposal narrative.", OpportunityTask.Priority.HIGH),
        ("Review budget", "Review budget detail against opportunity requirements.", OpportunityTask.Priority.HIGH),
        ("Prepare attachments", "Finalize supporting files for submission.", OpportunityTask.Priority.MEDIUM),
    ],
    Opportunity.LifecycleStatus.SUBMITTED: [
        ("Track confirmation", "Save submission confirmation and receipt details.", OpportunityTask.Priority.HIGH),
        ("Schedule follow-up", "Set a follow-up checkpoint for the opportunity owner.", OpportunityTask.Priority.MEDIUM),
    ],
    Opportunity.LifecycleStatus.AWARDED: [
        ("Prepare implementation plan", "Translate the award into implementation milestones.", OpportunityTask.Priority.HIGH),
        ("Track reporting requirements", "Capture reporting dates, metrics, and deliverables.", OpportunityTask.Priority.MEDIUM),
    ],
    Opportunity.LifecycleStatus.DECLINED: [
        ("Capture feedback", "Record reviewer feedback or internal lessons.", OpportunityTask.Priority.MEDIUM),
        ("Save lessons learned", "Document changes for the next opportunity cycle.", OpportunityTask.Priority.LOW),
    ],
}


@dataclass(frozen=True)
class RequirementItem:
    label: str
    value: str
    status: str


@dataclass(frozen=True)
class DeadlineDisplay:
    deadline: OpportunityDeadline
    computed_status: str
    is_overdue: bool
    is_due_soon: bool


@dataclass(frozen=True)
class TaskSummary:
    total_tasks: int
    open_tasks: int
    completed_tasks: int
    blocked_tasks: int
    overdue_tasks: int
    tasks: list[OpportunityTask]


@dataclass(frozen=True)
class DeadlineSummary:
    upcoming_deadlines: int
    due_soon_deadlines: int
    overdue_deadlines: int
    completed_deadlines: int
    next_deadline: DeadlineDisplay | None
    deadlines: list[DeadlineDisplay]


@dataclass(frozen=True)
class OpportunityWorkSummary:
    open_tasks: int
    overdue_tasks: int
    upcoming_deadlines: int
    overdue_deadlines: int
    next_critical_deadline: DeadlineDisplay | None
    drafting_opportunities: int
    submitted_opportunities: int


@dataclass(frozen=True)
class OpportunityWorkspaceContext:
    match: OpportunityMatch
    requirements: list[RequirementItem]
    task_summary: TaskSummary
    deadline_summary: DeadlineSummary
    recommended_next_step: str
    forecast: OpportunityForecastContribution


def _target_date(opportunity: Opportunity, days_before_deadline: int):
    if not opportunity.deadline:
        return None
    candidate = opportunity.deadline - timedelta(days=days_before_deadline)
    return min(candidate, opportunity.deadline)


def ensure_default_tasks(opportunity: Opportunity) -> list[OpportunityTask]:
    definitions = DEFAULT_TASKS_BY_STAGE.get(opportunity.lifecycle_status, [])
    for index, (title, description, priority) in enumerate(definitions):
        OpportunityTask.objects.get_or_create(
            opportunity=opportunity,
            title=title,
            defaults={
                "description": description,
                "priority": priority,
                "owner": opportunity.assigned_owner,
                "due_date": _target_date(opportunity, max(3, 21 - (index * 4))),
            },
        )
    return list(opportunity.tasks.select_related("owner").all())


def ensure_default_deadlines(opportunity: Opportunity) -> list[OpportunityDeadline]:
    if opportunity.deadline:
        OpportunityDeadline.objects.get_or_create(
            opportunity=opportunity,
            title="Submission deadline",
            defaults={
                "deadline_date": opportunity.deadline,
                "deadline_type": OpportunityDeadline.DeadlineType.SUBMISSION,
                "notes": "Primary opportunity deadline from the discovery inventory.",
            },
        )
        OpportunityDeadline.objects.get_or_create(
            opportunity=opportunity,
            title="Internal review deadline",
            defaults={
                "deadline_date": opportunity.deadline - timedelta(days=14),
                "deadline_type": OpportunityDeadline.DeadlineType.INTERNAL_REVIEW,
                "notes": "Internal checkpoint before final submission.",
            },
        )
    return list(opportunity.deadlines.all())


def deadline_display(deadline: OpportunityDeadline) -> DeadlineDisplay:
    today = timezone.localdate()
    if deadline.status == OpportunityDeadline.Status.COMPLETE:
        computed_status = OpportunityDeadline.Status.COMPLETE.label
        is_overdue = False
        is_due_soon = False
    elif deadline.deadline_date < today:
        computed_status = OpportunityDeadline.Status.OVERDUE.label
        is_overdue = True
        is_due_soon = False
    elif deadline.deadline_date <= today + timedelta(days=14):
        computed_status = OpportunityDeadline.Status.DUE_SOON.label
        is_overdue = False
        is_due_soon = True
    else:
        computed_status = OpportunityDeadline.Status.UPCOMING.label
        is_overdue = False
        is_due_soon = False
    return DeadlineDisplay(
        deadline=deadline,
        computed_status=computed_status,
        is_overdue=is_overdue,
        is_due_soon=is_due_soon,
    )


def build_task_summary(opportunity: Opportunity) -> TaskSummary:
    tasks = ensure_default_tasks(opportunity)
    today = timezone.localdate()
    return TaskSummary(
        total_tasks=len(tasks),
        open_tasks=sum(1 for task in tasks if task.status != OpportunityTask.Status.COMPLETE),
        completed_tasks=sum(1 for task in tasks if task.status == OpportunityTask.Status.COMPLETE),
        blocked_tasks=sum(1 for task in tasks if task.status == OpportunityTask.Status.BLOCKED),
        overdue_tasks=sum(
            1
            for task in tasks
            if task.due_date and task.due_date < today and task.status != OpportunityTask.Status.COMPLETE
        ),
        tasks=tasks,
    )


def build_deadline_summary(opportunity: Opportunity) -> DeadlineSummary:
    displays = [deadline_display(deadline) for deadline in ensure_default_deadlines(opportunity)]
    active = [
        display
        for display in displays
        if display.deadline.status != OpportunityDeadline.Status.COMPLETE
    ]
    active_sorted = sorted(active, key=lambda item: (item.deadline.deadline_date, item.deadline.title))
    return DeadlineSummary(
        upcoming_deadlines=sum(
            1
            for display in displays
            if display.computed_status == OpportunityDeadline.Status.UPCOMING.label
        ),
        due_soon_deadlines=sum(1 for display in displays if display.is_due_soon),
        overdue_deadlines=sum(1 for display in displays if display.is_overdue),
        completed_deadlines=sum(
            1
            for display in displays
            if display.deadline.status == OpportunityDeadline.Status.COMPLETE
        ),
        next_deadline=active_sorted[0] if active_sorted else None,
        deadlines=displays,
    )


def opportunity_requirements(opportunity: Opportunity) -> list[RequirementItem]:
    return [
        RequirementItem(
            "Eligibility requirements",
            opportunity.eligibility_notes or "Review opportunity eligibility and applicant fit.",
            "Complete" if opportunity.eligibility_notes else "Placeholder-ready",
        ),
        RequirementItem(
            "Required documents",
            "Prepare registrations, financials, program materials, and standard attachments.",
            "Placeholder-ready",
        ),
        RequirementItem(
            "Budget needs",
            "Capture budget narrative, line items, and requested amount assumptions.",
            "Placeholder-ready",
        ),
        RequirementItem(
            "Outcome data needed",
            "Gather measurable outcomes, participant counts, and impact evidence.",
            "Placeholder-ready",
        ),
        RequirementItem(
            "Partnership evidence needed",
            "Identify partner letters, referral relationships, and collaboration history.",
            "Placeholder-ready",
        ),
        RequirementItem(
            "Submission requirements",
            "Confirm portal, deadline, file format, and final review process.",
            "Placeholder-ready",
        ),
    ]


def build_opportunity_workspace(project, opportunity: Opportunity, funding_criteria=None) -> OpportunityWorkspaceContext:
    return OpportunityWorkspaceContext(
        match=score_inventory_opportunity(project, opportunity, funding_criteria),
        requirements=opportunity_requirements(opportunity),
        task_summary=build_task_summary(opportunity),
        deadline_summary=build_deadline_summary(opportunity),
        recommended_next_step=recommended_lifecycle_action(opportunity.lifecycle_status),
        forecast=forecast_contribution(opportunity),
    )


def build_work_summary(project=None) -> OpportunityWorkSummary:
    opp_qs = Opportunity.objects.all() if project is None else Opportunity.objects.filter(project=project)
    opportunities = list(opp_qs)
    for opportunity in opportunities:
        ensure_default_tasks(opportunity)
        ensure_default_deadlines(opportunity)
    opp_ids = [opp.pk for opp in opportunities]
    tasks = list(OpportunityTask.objects.filter(opportunity_id__in=opp_ids))
    deadline_displays = [
        deadline_display(deadline)
        for deadline in OpportunityDeadline.objects.filter(opportunity_id__in=opp_ids)
    ]
    active_deadlines = [
        display
        for display in deadline_displays
        if display.deadline.status != OpportunityDeadline.Status.COMPLETE
    ]
    active_deadlines = sorted(active_deadlines, key=lambda item: (item.deadline.deadline_date, item.deadline.title))
    today = timezone.localdate()
    return OpportunityWorkSummary(
        open_tasks=sum(1 for task in tasks if task.status != OpportunityTask.Status.COMPLETE),
        overdue_tasks=sum(
            1
            for task in tasks
            if task.due_date and task.due_date < today and task.status != OpportunityTask.Status.COMPLETE
        ),
        upcoming_deadlines=sum(
            1
            for display in deadline_displays
            if display.computed_status in {
                OpportunityDeadline.Status.UPCOMING.label,
                OpportunityDeadline.Status.DUE_SOON.label,
            }
        ),
        overdue_deadlines=sum(1 for display in deadline_displays if display.is_overdue),
        next_critical_deadline=active_deadlines[0] if active_deadlines else None,
        drafting_opportunities=sum(
            1
            for opportunity in opportunities
            if opportunity.lifecycle_status == Opportunity.LifecycleStatus.APPLICATION_DRAFTING
        ),
        submitted_opportunities=sum(
            1
            for opportunity in opportunities
            if opportunity.lifecycle_status == Opportunity.LifecycleStatus.SUBMITTED
        ),
    )
