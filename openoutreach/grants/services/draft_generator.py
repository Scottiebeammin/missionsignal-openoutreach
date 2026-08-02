"""Draft generation for Grant Builder.

The agent is a *writer*, never a *source*. It receives a closed set of labeled
organization facts and is forbidden from adding anything outside them. Where a
fact is missing it must emit the literal marker

    [Information needed: <what is missing>]

rather than estimating, rounding, or inferring. The marker is load-bearing: the
UI renders it as a visible gap and the completeness review counts it as an open
issue, so an un-filled placeholder can never quietly reach a funder.

Everything generated here lands in ``GrantApplicationSection.draft_response``.
Approved text lives in a different column and is never touched by this module.
"""
from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from openoutreach.grants.exceptions import DraftGenerationFailed, DraftGenerationUnavailable
from openoutreach.grants.services.context_builder import GrantContext, render_facts_block

logger = logging.getLogger(__name__)

INFORMATION_NEEDED_PREFIX = "[Information needed:"

# Refinement actions offered on an answer. Each is a writing instruction — none
# of them may introduce a new fact.
ACTIONS: dict[str, str] = {
    "improve": "Strengthen this response. Tighten the argument and make the language more direct and concrete.",
    "shorten": "Shorten this response. Remove repetition and filler. Every retained fact must survive.",
    "expand": "Expand this response using ONLY the supplied facts. If there is nothing further to say from the facts, say so rather than padding.",
    "specific": "Make this response more specific by drawing harder on the concrete details already present in the facts.",
    "clarity": "Improve clarity and readability. Plain sentences, no jargon, no filler.",
    "align": "Align this response more closely to the funder's stated priorities, without adding any new claim about the organization.",
}

ACTION_LABELS: dict[str, str] = {
    "improve": "Improve",
    "shorten": "Shorten",
    "expand": "Expand",
    "specific": "Make More Specific",
    "clarity": "Improve Clarity",
    "align": "Align to Funder",
}


class SectionDraft(BaseModel):
    """Structured drafter output."""

    response: str = Field(description="The grant response text.")
    sources_used: list[str] = Field(
        default_factory=list,
        description="Labels of the supplied facts this response actually drew on.",
    )
    missing_information: list[str] = Field(
        default_factory=list,
        description="Facts a strong answer needs that were not supplied.",
    )


_SYSTEM_RULES = """You write grant application responses for Anansi Atlas, on behalf of a nonprofit organization.

ABSOLUTE RULE — FACTUAL INTEGRITY
You may only state facts that appear in the ORGANIZATION FACTS or OPPORTUNITY FACTS blocks below.
You must NEVER invent, estimate, infer, round, or illustrate any of the following:
statistics, outcomes, budgets, dollar amounts, staff numbers, populations served, years,
dates, funder relationships, partnerships, government relationships, prior grant awards,
program performance, or geographic coverage.

If a strong answer needs something that was not supplied, do not supply it yourself.
Write the exact marker `[Information needed: <short description>]` in the sentence where the
fact belongs, and list the same item in missing_information.

You may improve wording, structure, order, emphasis, and clarity. You may not add substance.
Never describe the organization as "leading", "award-winning", "renowned", or similar unless
that claim appears verbatim in the supplied facts.

STYLE
Write in the organization's voice, in third person, as continuous prose a program officer would
read. No headings, no bullet lists, no markdown, no preamble, no meta-commentary about the task.

SOURCES
List in sources_used the exact labels (e.g. "Organization Mission") of the facts you actually used.
Do not list a fact you did not use."""


def _agent(output_type):
    """Build the drafting agent, or fail with a message the UI can show."""
    from openoutreach.core.llm import get_llm_model

    try:
        model = get_llm_model()
    except ValueError as exc:
        raise DraftGenerationUnavailable(str(exc)) from exc
    except ImportError as exc:  # provider SDK missing from this build
        raise DraftGenerationUnavailable(
            f"The configured LLM provider is not installed in this environment: {exc}"
        ) from exc

    from pydantic_ai import Agent

    return Agent(
        model,
        output_type=output_type,
        system_prompt=_SYSTEM_RULES,
        model_settings={"temperature": 0.2, "timeout": 90},
    )


def _run(agent, prompt: str) -> SectionDraft:
    from openoutreach.core.llm import run_agent_sync

    draft = run_agent_sync(agent.run(prompt)).output
    if not (draft.response or "").strip():
        raise DraftGenerationFailed("The drafting agent returned an empty response.")
    return draft


def _limit_instruction(section) -> str:
    if section.character_limit:
        return (
            f"\nHARD LIMIT: the response must be at most {section.character_limit} characters. "
            "Stay under it without dropping any supplied fact."
        )
    if section.word_limit:
        return (
            f"\nHARD LIMIT: the response must be at most {section.word_limit} words. "
            "Stay under it without dropping any supplied fact."
        )
    return ""


def _reusable_block(reusable) -> str:
    """Approved library answers offered as prior art, not as a template to copy."""
    if not reusable:
        return ""
    blocks = "\n\n".join(
        f"[{item.get_category_display()}] {item.title}\n{item.answer}" for item in reusable
    )
    return (
        "\n\nPREVIOUSLY APPROVED ANSWERS FROM THIS ORGANIZATION\n"
        "These were approved by the organization, so the facts in them are trustworthy and "
        "reusable. Adapt them to this funder's question rather than starting over. Do not copy "
        "any claim from them that contradicts the facts above.\n\n" + blocks
    )


def _prompt(section, context: GrantContext, spec, reusable=(), instruction: str = "", existing: str = "") -> str:
    facts = render_facts_block(context, spec.fact_keys)
    opportunity_keys = (
        "opportunity.name", "opportunity.funder", "opportunity.focus_areas",
        "opportunity.beneficiaries", "opportunity.geography", "opportunity.eligibility_notes",
        "opportunity.applicant_types", "opportunity.funding_amount", "opportunity.deadline",
    )
    opportunity_facts = render_facts_block(context, opportunity_keys)
    guidance = "\n".join(f"- {item}" for item in (section.guidance or spec.guidance))

    parts = [
        f"SECTION: {section.title}",
        f"FUNDER QUESTION:\n{section.funder_question or spec.question}",
        f"WHAT A STRONG RESPONSE NEEDS:\n{guidance}",
        f"ORGANIZATION FACTS (the only permitted source of substance):\n{facts}",
        f"OPPORTUNITY FACTS (verified funder data — use to tailor, not to invent):\n{opportunity_facts}",
    ]
    if spec.drafting_note:
        parts.append(f"SECTION-SPECIFIC RULE:\n{spec.drafting_note}")
    if existing:
        parts.append(f"CURRENT RESPONSE (revise this, keep every supported fact):\n{existing}")
    if instruction:
        parts.append(f"REVISION INSTRUCTION:\n{instruction}")

    return "\n\n".join(parts) + _reusable_block(reusable) + _limit_instruction(section)


def generate_section_draft(section, context: GrantContext, spec, reusable=()) -> SectionDraft:
    """Write a first draft for one section from the organization's own facts."""
    agent = _agent(SectionDraft)
    return _run(agent, _prompt(section, context, spec, reusable=reusable))


def refine_section_draft(section, context: GrantContext, spec, action: str, text: str) -> SectionDraft:
    """Apply a writing action (Improve / Shorten / …) to text the user already has.

    ``text`` is passed in by the caller so an approved answer can be refined into
    a NEW draft without the approved column ever being modified in place.
    """
    instruction = ACTIONS.get(action)
    if instruction is None:
        raise DraftGenerationFailed(f"Unknown refinement action: {action!r}")
    agent = _agent(SectionDraft)
    return _run(agent, _prompt(section, context, spec, instruction=instruction, existing=text))
