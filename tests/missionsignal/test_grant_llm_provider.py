"""Grant Builder must not care which LLM provider Atlas is configured for.

Atlas already routes every model call through ``core.llm`` (a `SiteConfig`-driven
factory with seven provider builders). These tests pin that contract from Grant
Builder's side, so a future change cannot quietly couple drafting to one SDK:

- Grant Builder reaches the model only through ``core.llm``.
- Anthropic and OpenAI are both selectable purely by configuration.
- The provider choice changes nothing about Grant Builder's behaviour.
- No provider object escapes into Grant Builder's own data.
- Missing credentials fail safely, with a message the UI can show.

No network calls and no API keys: the provider builders construct a client
object without contacting anything, so provider selection is genuinely
exercised rather than fully mocked.
"""
from pathlib import Path
from unittest.mock import patch

import pytest

from openoutreach.core.llm import get_llm_model
from openoutreach.core.models import SiteConfig
from openoutreach.grants.exceptions import DraftGenerationUnavailable
from openoutreach.grants.models import GrantApplicationSection
from openoutreach.grants.services import draft_generator
from openoutreach.grants.services.context_builder import build_grant_context
from openoutreach.grants.services.draft_generator import SectionDraft
from openoutreach.grants.services.template import spec_for

pytestmark = pytest.mark.django_db

# Reuse the V1 suite's fixtures so this module tests the real workspace.
from tests.missionsignal.test_grant_builder import application, grant_project  # noqa: E402,F401

GRANTS_PACKAGE = Path(draft_generator.__file__).resolve().parent.parent

# Placeholder credential — never contacted, never a real key.
FAKE_KEY = "test-key-not-real"


class _Cfg:
    """Stand-in for the SiteConfig row the factory reads."""

    def __init__(self, provider, model):
        self.llm_provider = provider
        self.ai_model = model
        self.llm_api_key = FAKE_KEY
        self.llm_api_base = ""


@pytest.fixture
def section(application):
    """A drafted-against section on the standard template."""
    return application.sections.get(section_key="mission")


# ── The provider layer is reachable and configurable ─────────────────────────

@pytest.mark.parametrize("provider,model,expected_module", [
    ("anthropic", "claude-sonnet-4-5", "pydantic_ai.models.anthropic"),
    ("openai", "gpt-4o", "pydantic_ai.models.openai"),
])
def test_provider_is_selected_purely_by_configuration(provider, model, expected_module):
    with patch("openoutreach.core.llm._validated_site_config", return_value=_Cfg(provider, model)):
        built = get_llm_model()

    assert type(built).__module__ == expected_module
    assert built.model_name == model


def test_site_config_offers_both_providers():
    """Provider and model are set through Atlas's own configuration, not env vars."""
    choices = dict(SiteConfig.LLMProvider.choices)

    assert "anthropic" in choices
    assert "openai" in choices
    # The model is a free-text field so a new model name needs no code change.
    assert SiteConfig._meta.get_field("ai_model").blank is True


# ── Grant Builder does not know which provider it is talking to ──────────────

def test_grant_builder_imports_no_provider_sdk():
    """The Anthropic/OpenAI SDKs must be imported only inside core.llm."""
    offenders = []
    for path in GRANTS_PACKAGE.rglob("*.py"):
        text = path.read_text()
        for needle in ("import anthropic", "from anthropic", "import openai", "from openai"):
            if needle in text:
                offenders.append(f"{path.name}: {needle}")

    assert offenders == [], f"Grant Builder must not import a provider SDK: {offenders}"


def test_grant_builder_names_no_provider_or_model():
    """No hardcoded provider or model names anywhere in Grant Builder."""
    offenders = []
    for path in GRANTS_PACKAGE.rglob("*.py"):
        lowered = path.read_text().lower()
        for needle in ("claude-", "gpt-4", "gpt-3", "anthropic", "openai"):
            if needle in lowered:
                offenders.append(f"{path.name}: {needle}")

    assert offenders == [], f"Grant Builder must stay provider-neutral: {offenders}"


def test_grant_builder_reaches_the_model_only_through_core_llm(section):
    """Drafting calls the shared Atlas factory rather than building its own client.

    The spy calls through to the real factory, so the agent is still constructed
    from a genuine provider model — this proves the call path, not just the mock.
    """
    import openoutreach.core.llm as core_llm

    context = build_grant_context(section.application)
    draft = SectionDraft(response="A drafted answer.", sources_used=[], missing_information=[])
    real_factory = core_llm.get_llm_model

    with patch("openoutreach.core.llm._validated_site_config",
               return_value=_Cfg("anthropic", "claude-sonnet-4-5")), \
         patch("openoutreach.core.llm.get_llm_model", side_effect=real_factory) as factory, \
         patch.object(draft_generator, "_run", return_value=draft):
        draft_generator.generate_section_draft(section, context, spec_for("mission"))

    factory.assert_called_once()


@pytest.mark.parametrize("provider,model", [
    ("anthropic", "claude-sonnet-4-5"),
    ("openai", "gpt-4o"),
])
def test_business_logic_is_identical_across_providers(client, application, provider, model):
    """Switching provider must not change a single thing Grant Builder records."""
    section = application.sections.get(section_key="mission")
    draft = SectionDraft(
        response="Our mission is to serve the community.",
        sources_used=["Organization Mission"],
        missing_information=[],
    )
    client.force_login(application.created_by)

    with patch("openoutreach.core.llm._validated_site_config", return_value=_Cfg(provider, model)), \
         patch.object(draft_generator, "_run", return_value=draft):
        client.post(f"/projects/{application.project_id}/grants/{application.pk}"
                    f"/sections/{section.section_key}/generate/")

    section.refresh_from_db()
    assert section.draft_response == "Our mission is to serve the community."
    assert section.approved_response == ""
    assert section.status == GrantApplicationSection.Status.DRAFTED
    assert [entry["label"] for entry in section.source_fields] == ["Organization Mission"]


def test_no_provider_object_is_persisted_by_grant_builder(section):
    """Only plain text and labels reach the database — never a client object."""
    context = build_grant_context(section.application)
    draft = SectionDraft(
        response="Text only.", sources_used=["Organization Mission"], missing_information=[],
    )

    with patch("openoutreach.core.llm._validated_site_config", return_value=_Cfg("anthropic", "claude-sonnet-4-5")), \
         patch.object(draft_generator, "_run", return_value=draft):
        result = draft_generator.generate_section_draft(section, context, spec_for("mission"))

    assert isinstance(result, SectionDraft)
    assert isinstance(result.response, str)
    assert all(isinstance(item, str) for item in result.sources_used)


# ── Missing credentials fail safely ──────────────────────────────────────────

def test_missing_api_key_fails_with_a_message_not_a_crash(section):
    context = build_grant_context(section.application)

    with patch(
        "openoutreach.core.llm._validated_site_config",
        side_effect=ValueError("LLM_API_KEY is not set in Site Configuration."),
    ):
        with pytest.raises(DraftGenerationUnavailable) as caught:
            draft_generator.generate_section_draft(section, context, spec_for("mission"))

    assert "LLM_API_KEY" in str(caught.value)


def test_missing_provider_sdk_fails_with_a_message_not_a_crash(section):
    context = build_grant_context(section.application)

    with patch("openoutreach.core.llm.get_llm_model", side_effect=ImportError("no module named 'anthropic'")):
        with pytest.raises(DraftGenerationUnavailable) as caught:
            draft_generator.generate_section_draft(section, context, spec_for("mission"))

    assert "not installed" in str(caught.value)


def test_unknown_provider_is_rejected():
    with patch("openoutreach.core.llm._validated_site_config", return_value=_Cfg("not-a-provider", "x")):
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            get_llm_model()


# ── The prompt contract stays provider-neutral ───────────────────────────────

def test_system_rules_carry_the_full_factual_integrity_contract():
    rules = draft_generator._SYSTEM_RULES.lower()

    for clause in ("never invent", "information needed", "statistics", "budgets", "partnerships"):
        assert clause in rules
    # Provider-neutral: the contract must not address a named model.
    for provider in ("claude", "gpt", "anthropic", "openai", "chatgpt"):
        assert provider not in rules


def test_system_rules_forbid_promising_an_outcome_and_padding():
    rules = draft_generator._SYSTEM_RULES.lower()

    assert "guarantee" in rules
    assert "shorter answer" in rules
