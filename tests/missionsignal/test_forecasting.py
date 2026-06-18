from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from openoutreach.funding.models import Opportunity
from openoutreach.signals.demo import seed_missionsignal_demo
from openoutreach.signals.forecasting import build_pipeline_forecast, forecast_contribution


pytestmark = pytest.mark.django_db


@pytest.fixture
def forecast_project(db):
    user, _organization, project = seed_missionsignal_demo()
    Opportunity.objects.filter(name="Digital Equity Grant").update(
        lifecycle_status=Opportunity.LifecycleStatus.QUALIFIED,
    )
    Opportunity.objects.filter(name="Youth Technology Initiative").update(
        lifecycle_status=Opportunity.LifecycleStatus.SUBMITTED,
    )
    Opportunity.objects.filter(name="Technology Equipment Donation Round").update(
        lifecycle_status=Opportunity.LifecycleStatus.AWARDED,
    )
    return project, user


def test_opportunity_estimated_value_model_behavior():
    opportunity = Opportunity.objects.create(name="Forecast Grant")

    assert opportunity.estimated_value is None
    assert opportunity.value_confidence == Opportunity.ValueConfidence.MEDIUM
    assert opportunity.forecast_notes == ""

    opportunity.estimated_value = Decimal("50000.00")
    opportunity.value_confidence = Opportunity.ValueConfidence.HIGH
    opportunity.forecast_notes = "Board-approved target request."
    opportunity.save(update_fields=["estimated_value", "value_confidence", "forecast_notes", "updated_at"])
    opportunity.refresh_from_db()

    assert opportunity.estimated_value == Decimal("50000.00")
    assert opportunity.get_value_confidence_display() == "High"
    assert opportunity.forecast_notes == "Board-approved target request."


def test_forecast_calculation_helper_uses_lifecycle_weights(forecast_project):
    grant = Opportunity.objects.get(name="Digital Equity Grant")
    contract = Opportunity.objects.get(name="Youth Technology Initiative")
    equipment = Opportunity.objects.get(name="Technology Equipment Donation Round")

    grant_forecast = forecast_contribution(grant)
    contract_forecast = forecast_contribution(contract)
    equipment_forecast = forecast_contribution(equipment)
    forecast = build_pipeline_forecast()

    assert grant_forecast.stage_weight_percent == 25
    assert grant_forecast.weighted_value == Decimal("18750.00")
    assert contract_forecast.stage_weight_percent == 70
    assert contract_forecast.weighted_value == Decimal("168000.00")
    assert equipment_forecast.stage_weight_percent == 100
    assert equipment_forecast.weighted_value == Decimal("40000.00")
    assert forecast.total_pipeline_value > forecast.weighted_forecast_value
    assert forecast.submitted_value >= Decimal("240000.00")
    assert forecast.awarded_value >= Decimal("40000.00")
    assert forecast.forecast_confidence in {"Low", "Medium", "High"}
    assert forecast.highest_value_opportunity is not None
    assert forecast.highest_confidence_opportunity is not None
    assert forecast.by_opportunity_type
    assert forecast.by_lifecycle_stage
    assert forecast.by_priority_level
    assert forecast.by_confidence_level


def test_demo_seed_adds_varied_opportunity_values(forecast_project):
    values = list(Opportunity.objects.exclude(estimated_value__isnull=True).values_list("estimated_value", flat=True))

    assert len(values) >= 20
    assert min(values) < Decimal("10000.00")
    assert max(values) >= Decimal("200000.00")
    assert Opportunity.objects.filter(value_confidence=Opportunity.ValueConfidence.HIGH).exists()
    assert Opportunity.objects.filter(value_confidence=Opportunity.ValueConfidence.LOW).exists()


def test_dashboard_pipeline_workspace_and_ecosystem_render_forecast(client, forecast_project):
    project, user = forecast_project
    client.force_login(user)

    dashboard = client.get(reverse("project-dashboard", kwargs={"pk": project.pk})).content.decode()
    pipeline = client.get(reverse("project-pipeline", kwargs={"pk": project.pk})).content.decode()
    ecosystem = client.get(reverse("project-ecosystem", kwargs={"pk": project.pk})).content.decode()

    assert "Forecast Summary" in dashboard
    assert "Total Pipeline Value" in dashboard
    assert "Weighted Forecast Value" in dashboard
    assert "Highest Value Opportunity" in dashboard
    assert "Highest Confidence Opportunity" in dashboard
    assert "Pipeline Forecast" in pipeline
    assert "Total Value" in pipeline
    assert "Weighted Value" in pipeline
    assert "Upcoming Deadline Value" in pipeline
    assert "Forecast Health" in ecosystem
    assert "Forecast Confidence" in ecosystem
    assert "Funding Forecast Breakdown" in ecosystem


def test_opportunity_workspace_discovery_and_matching_render_forecast(client, forecast_project):
    project, user = forecast_project
    opportunity = Opportunity.objects.get(name="Digital Equity Grant")
    client.force_login(user)

    workspace = client.get(
        reverse("project-opportunity-workspace", kwargs={"pk": project.pk, "opportunity_id": opportunity.pk}),
    ).content.decode()
    discovery = client.get(reverse("project-discovery", kwargs={"pk": project.pk})).content.decode()
    matching = client.get(reverse("project-matches", kwargs={"pk": project.pk})).content.decode()

    assert "Estimated Value" in workspace
    assert "Value Confidence" in workspace
    assert "Weighted Forecast Contribution" in workspace
    assert "Forecast Notes" in workspace
    assert "Estimated Value" in discovery
    assert "Value $" in discovery
    assert "Estimated Value:" in matching
    assert "Weighted Value:" in matching


def test_non_member_forecast_pages_remain_protected(client, forecast_project):
    project, _user = forecast_project
    opportunity = Opportunity.objects.get(name="Digital Equity Grant")
    outsider = get_user_model().objects.create_user(username="forecast-outsider")
    client.force_login(outsider)

    assert client.get(reverse("project-dashboard", kwargs={"pk": project.pk})).status_code == 404
    assert client.get(reverse("project-pipeline", kwargs={"pk": project.pk})).status_code == 404
    assert client.get(reverse("project-ecosystem", kwargs={"pk": project.pk})).status_code == 404
    assert client.get(
        reverse("project-opportunity-workspace", kwargs={"pk": project.pk, "opportunity_id": opportunity.pk}),
    ).status_code == 404
