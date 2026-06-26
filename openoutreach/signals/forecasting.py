from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.utils import timezone

from openoutreach.funding.models import Opportunity
from openoutreach.signals.lifecycle import ACTIVE_LIFECYCLE_STATUSES


STAGE_WEIGHTS = {
    Opportunity.LifecycleStatus.DISCOVERED: Decimal("0.10"),
    Opportunity.LifecycleStatus.REVIEWING: Decimal("0.15"),
    Opportunity.LifecycleStatus.QUALIFIED: Decimal("0.25"),
    Opportunity.LifecycleStatus.PURSUING: Decimal("0.40"),
    Opportunity.LifecycleStatus.APPLICATION_DRAFTING: Decimal("0.55"),
    Opportunity.LifecycleStatus.SUBMITTED: Decimal("0.70"),
    Opportunity.LifecycleStatus.AWARDED: Decimal("1.00"),
    Opportunity.LifecycleStatus.DECLINED: Decimal("0.00"),
    Opportunity.LifecycleStatus.CLOSED: Decimal("0.00"),
}

CONFIDENCE_RANK = {
    Opportunity.ValueConfidence.HIGH: 3,
    Opportunity.ValueConfidence.MEDIUM: 2,
    Opportunity.ValueConfidence.LOW: 1,
}


@dataclass(frozen=True)
class ForecastBreakdown:
    label: str
    count: int
    total_value: Decimal
    weighted_value: Decimal


@dataclass(frozen=True)
class OpportunityForecastContribution:
    estimated_value: Decimal | None
    value_confidence: str
    forecast_notes: str
    stage_weight_percent: int
    weighted_value: Decimal


@dataclass(frozen=True)
class PipelineForecast:
    total_pipeline_value: Decimal
    active_pipeline_value: Decimal
    submitted_value: Decimal
    awarded_value: Decimal
    declined_closed_value: Decimal
    weighted_forecast_value: Decimal
    forecast_confidence: str
    highest_value_opportunity: Opportunity | None
    highest_confidence_opportunity: Opportunity | None
    highest_priority_value: Decimal
    upcoming_deadline_value: Decimal
    by_opportunity_type: list[ForecastBreakdown]
    by_lifecycle_stage: list[ForecastBreakdown]
    by_priority_level: list[ForecastBreakdown]
    by_confidence_level: list[ForecastBreakdown]


def _money(value) -> Decimal:
    if value is None:
        return Decimal("0.00")
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def forecast_contribution(opportunity: Opportunity) -> OpportunityForecastContribution:
    weight = STAGE_WEIGHTS.get(opportunity.lifecycle_status, Decimal("0.00"))
    value = _money(opportunity.estimated_value)
    return OpportunityForecastContribution(
        estimated_value=opportunity.estimated_value,
        value_confidence=opportunity.get_value_confidence_display(),
        forecast_notes=opportunity.forecast_notes,
        stage_weight_percent=int(weight * 100),
        weighted_value=_money(value * weight),
    )


def _breakdown(opportunities: list[Opportunity], choices, attr: str) -> list[ForecastBreakdown]:
    rows = []
    for value, label in choices:
        matching = [opportunity for opportunity in opportunities if getattr(opportunity, attr) == value]
        rows.append(
            ForecastBreakdown(
                label=label,
                count=len(matching),
                total_value=sum((_money(opportunity.estimated_value) for opportunity in matching), Decimal("0.00")),
                weighted_value=sum((forecast_contribution(opportunity).weighted_value for opportunity in matching), Decimal("0.00")),
            )
        )
    return rows


def _forecast_confidence(opportunities: list[Opportunity]) -> str:
    valued = [opportunity for opportunity in opportunities if opportunity.estimated_value is not None]
    if not valued:
        return "Low"
    confidence_points = sum(CONFIDENCE_RANK.get(opportunity.value_confidence, 1) for opportunity in valued)
    average = confidence_points / len(valued)
    coverage = len(valued) / len(opportunities) if opportunities else 0
    if average >= 2.5 and coverage >= 0.7:
        return "High"
    if average >= 1.75 and coverage >= 0.45:
        return "Medium"
    return "Low"


def build_pipeline_forecast(project=None) -> PipelineForecast:
    qs = Opportunity.objects.select_related("source_organization", "assigned_owner").order_by("deadline", "name")
    if project is not None:
        qs = qs.filter(project=project)
    opportunities = list(qs)
    active = [
        opportunity
        for opportunity in opportunities
        if opportunity.lifecycle_status in ACTIVE_LIFECYCLE_STATUSES
    ]
    submitted = [
        opportunity
        for opportunity in opportunities
        if opportunity.lifecycle_status == Opportunity.LifecycleStatus.SUBMITTED
    ]
    awarded = [
        opportunity
        for opportunity in opportunities
        if opportunity.lifecycle_status == Opportunity.LifecycleStatus.AWARDED
    ]
    declined_closed = [
        opportunity
        for opportunity in opportunities
        if opportunity.lifecycle_status in {
            Opportunity.LifecycleStatus.DECLINED,
            Opportunity.LifecycleStatus.CLOSED,
        }
    ]
    today = timezone.localdate()
    upcoming_deadline = [
        opportunity
        for opportunity in active
        if opportunity.deadline and today <= opportunity.deadline <= today + timedelta(days=45)
    ]
    high_priority = [
        opportunity
        for opportunity in opportunities
        if opportunity.priority_level == Opportunity.PriorityLevel.HIGH
    ]
    valued = [opportunity for opportunity in opportunities if opportunity.estimated_value is not None]
    highest_value = (
        sorted(valued, key=lambda opportunity: (-_money(opportunity.estimated_value), opportunity.name))[0]
        if valued else None
    )
    highest_confidence = (
        sorted(
            valued,
            key=lambda opportunity: (
                -CONFIDENCE_RANK.get(opportunity.value_confidence, 0),
                -_money(opportunity.estimated_value),
                opportunity.name,
            ),
        )[0]
        if valued else None
    )
    return PipelineForecast(
        total_pipeline_value=sum((_money(opportunity.estimated_value) for opportunity in opportunities), Decimal("0.00")),
        active_pipeline_value=sum((_money(opportunity.estimated_value) for opportunity in active), Decimal("0.00")),
        submitted_value=sum((_money(opportunity.estimated_value) for opportunity in submitted), Decimal("0.00")),
        awarded_value=sum((_money(opportunity.estimated_value) for opportunity in awarded), Decimal("0.00")),
        declined_closed_value=sum((_money(opportunity.estimated_value) for opportunity in declined_closed), Decimal("0.00")),
        weighted_forecast_value=sum((forecast_contribution(opportunity).weighted_value for opportunity in opportunities), Decimal("0.00")),
        forecast_confidence=_forecast_confidence(opportunities),
        highest_value_opportunity=highest_value,
        highest_confidence_opportunity=highest_confidence,
        highest_priority_value=sum((_money(opportunity.estimated_value) for opportunity in high_priority), Decimal("0.00")),
        upcoming_deadline_value=sum((_money(opportunity.estimated_value) for opportunity in upcoming_deadline), Decimal("0.00")),
        by_opportunity_type=_breakdown(opportunities, Opportunity.OpportunityType.choices, "opportunity_type"),
        by_lifecycle_stage=_breakdown(opportunities, Opportunity.LifecycleStatus.choices, "lifecycle_status"),
        by_priority_level=_breakdown(opportunities, Opportunity.PriorityLevel.choices, "priority_level"),
        by_confidence_level=_breakdown(opportunities, Opportunity.ValueConfidence.choices, "value_confidence"),
    )
