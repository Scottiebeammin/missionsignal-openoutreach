"""Switching the drafting model must not be an outage.

`temperature` was hardcoded at five call sites. Haiku 4.5 accepts it; Opus 5 and
Sonnet 5 reject it with a 400. So changing the model in SiteConfig — a
configuration change made in an admin form — would have broken drafting entirely,
with the failure surfacing once per draft rather than once up front.
"""
from __future__ import annotations

import pytest

from openoutreach.core.llm import agent_settings
from openoutreach.core.models import SiteConfig

pytestmark = pytest.mark.django_db


def _model(name):
    cfg = SiteConfig.objects.first() or SiteConfig.objects.create()
    cfg.ai_model = name
    cfg.save()
    return cfg


@pytest.mark.parametrize("model", ["claude-opus-5", "claude-sonnet-5", "claude-fable-5"])
def test_temperature_is_dropped_for_models_that_reject_it(model):
    _model(model)
    assert "temperature" not in agent_settings(temperature=0.7)
    assert agent_settings()["timeout"] == 60


@pytest.mark.parametrize("model", ["claude-haiku-4-5", "claude-haiku-4-5-20251001"])
def test_temperature_is_kept_for_models_that_accept_it(model):
    _model(model)
    assert agent_settings(temperature=0.7)["temperature"] == 0.7


def test_zero_temperature_is_preserved_not_treated_as_absent():
    # summaries.py wants deterministic output at 0.0. A truthiness bug here would
    # silently restore default sampling on the summarisers.
    _model("claude-haiku-4-5")
    assert agent_settings(temperature=0.0)["temperature"] == 0.0


def test_an_unreadable_config_does_not_break_drafting():
    SiteConfig.objects.all().delete()
    assert "timeout" in agent_settings()
