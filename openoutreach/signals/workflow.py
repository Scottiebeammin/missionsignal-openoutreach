from dataclasses import dataclass

from django.db.models import Case, IntegerField, Value, When

from openoutreach.funding.models import DocumentVaultItem, Opportunity


@dataclass(frozen=True)
class WorkflowStage:
    key: str
    label: str
    short_label: str
    description: str
    href_name: str


@dataclass(frozen=True)
class WorkflowStageView:
    key: str
    label: str
    short_label: str
    description: str
    href_name: str
    is_current: bool
    is_recommended_next: bool


@dataclass(frozen=True)
class WorkflowGuidance:
    current_stage: WorkflowStageView
    recommended_next_stage: WorkflowStageView
    stages: tuple[WorkflowStageView, ...]
    context_statement: str
    next_actions: tuple[str, ...]


WORKFLOW_STAGES = (
    WorkflowStage(
        key="understand",
        label="Understand Your Ecosystem",
        short_label="Understand",
        description="See the opportunity ecosystem around your mission.",
        href_name="project-opportunity-web",
    ),
    WorkflowStage(
        key="prioritize",
        label="Prioritize Opportunities",
        short_label="Prioritize",
        description="Choose the pathways most aligned to your mission.",
        href_name="project-opportunities",
    ),
    WorkflowStage(
        key="prepare",
        label="Prepare To Win",
        short_label="Prepare",
        description="Close readiness, document, and evidence gaps.",
        href_name="project-readiness",
    ),
    WorkflowStage(
        key="connect",
        label="Activate Relationships",
        short_label="Connect",
        description="Use partners, funders, and contacts to accelerate progress.",
        href_name="project-relationships",
    ),
    WorkflowStage(
        key="execute",
        label="Execute Pursuits",
        short_label="Execute",
        description="Manage active opportunities through the pipeline.",
        href_name="project-pipeline",
    ),
)

CONTEXT_STATEMENTS = {
    "understand": "Understand the ecosystem around your mission.",
    "prioritize": "Prioritize the opportunities most aligned to your mission.",
    "prepare": "Prepare your organization to pursue opportunities successfully.",
    "connect": "Activate the people and organizations that can accelerate your mission.",
    "execute": "Manage active pursuits and execution.",
}


def build_workflow_guidance(project, current_stage: str, primary_actions=()):
    stage_keys = [stage.key for stage in WORKFLOW_STAGES]
    if current_stage not in stage_keys:
        current_stage = "understand"
    current_index = stage_keys.index(current_stage)
    next_key = stage_keys[(current_index + 1) % len(stage_keys)]
    stage_views = tuple(
        WorkflowStageView(
            key=stage.key,
            label=stage.label,
            short_label=stage.short_label,
            description=stage.description,
            href_name=stage.href_name,
            is_current=stage.key == current_stage,
            is_recommended_next=stage.key == next_key,
        )
        for stage in WORKFLOW_STAGES
    )
    stage_by_key = {stage.key: stage for stage in stage_views}
    actions = _recommended_next_actions(project, current_stage, primary_actions)
    return WorkflowGuidance(
        current_stage=stage_by_key[current_stage],
        recommended_next_stage=stage_by_key[next_key],
        stages=stage_views,
        context_statement=CONTEXT_STATEMENTS[current_stage],
        next_actions=tuple(actions[:3]),
    )


def _recommended_next_actions(project, current_stage, primary_actions):
    actions = [action for action in primary_actions if action]
    missing_document = (
        DocumentVaultItem.objects
        .filter(project=project, status=DocumentVaultItem.Status.MISSING)
        .order_by("title")
        .first()
    )
    top_pathway = (
        Opportunity.objects
        .exclude(status=Opportunity.Status.ARCHIVED)
        .annotate(
            priority_rank=Case(
                When(priority_level=Opportunity.PriorityLevel.HIGH, then=Value(0)),
                When(priority_level=Opportunity.PriorityLevel.MEDIUM, then=Value(1)),
                default=Value(2),
                output_field=IntegerField(),
            ),
        )
        .order_by("priority_rank", "deadline", "name")
        .first()
    )

    if missing_document:
        actions.append(f"Complete missing readiness document: {missing_document.title}.")
    if top_pathway:
        actions.append(f"Review top pathway: {top_pathway.name}.")

    stage_specific_actions = {
        "understand": "Open the Snapshot to turn the web into a focused executive takeaway.",
        "prioritize": "Compare top pathways against readiness gaps before choosing what to pursue.",
        "prepare": "Resolve the highest readiness gap before moving the next pathway forward.",
        "connect": "Identify the relationship gap most likely to improve the next pursuit.",
        "execute": "Return to the Snapshot after pipeline updates to refresh the executive story.",
    }
    actions.append(stage_specific_actions[current_stage])

    unique_actions = []
    for action in actions:
        if action not in unique_actions:
            unique_actions.append(action)
    return unique_actions
