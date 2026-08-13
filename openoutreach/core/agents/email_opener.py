# openoutreach/core/agents/email_opener.py
"""Email opener agent: composes the single Layer-1 cold email for a deal.

A distinct entrypoint from the follow-up agent. Layer 1 email is one outbound
touch — no thread to read, no send/wait/give-up decision — so the structured
output is just a subject + body. The prompt shares the outreach base (identity,
product docs, lead summary, Mom Test strategy, language/no-placeholder rules) via
``email_opener.j2`` and only adds the cold-email framing + the subject request.
The multi-turn email conversation is the hosted Layer-2 backend's job.
"""
from __future__ import annotations

import logging

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from openoutreach.core.agents.prompt import base_context, render
from openoutreach.core.llm import agent_settings, get_llm_model, run_agent_sync

logger = logging.getLogger(__name__)


class EmailDraft(BaseModel):
    """Structured output from the email opener agent.

    ``primary_angle`` and ``angle_detail`` are optional and default to empty, so the
    Layer-1 deal path is unaffected. The cohort path asks for them and persists them
    on an ``OutreachMessage``, which is how a later follow-up can tell whether it is
    raising a new reason to care or restating the opener.
    """

    subject: str = Field(description="The email subject line — short, specific, like a real person wrote it; not salesy.")
    body: str = Field(description="The email body. A few short sentences; no signature, no placeholders.")
    primary_angle: str = Field(
        default="",
        description=(
            "The single reason THIS reader might care, as one snake_case value from the "
            "angle list in the prompt. The reason, not the source database — 'why they "
            "should care', not 'where we looked'. Empty only if no list was supplied."
        ),
    )
    angle_detail: str = Field(
        default="",
        description=(
            "The concrete argument behind primary_angle, in a few words, e.g. "
            "'DJJ-contracted youth shelter across the 5th Circuit' or 'county-provided technical "
            "assistance program'. Empty if the angle is category-level with no specific."
        ),
    )
    personalization: str = Field(
        default="",
        description=(
            "Honest self-classification: 'personalized' only if a verified fact about "
            "THIS reader materially changes the reasoning, otherwise 'category_relevant'. "
            "Category-relevant is a legitimate email; do not claim personalized to look better."
        ),
    )


def compose_opener_email(session, deal) -> EmailDraft:
    """Compose the opener subject + body for ``deal`` from its summaries + campaign docs."""
    system_prompt = render("email_opener.j2", **base_context(session, deal))

    agent = Agent(
        get_llm_model(),
        output_type=EmailDraft,
        model_settings=agent_settings(temperature=0.7),
    )
    draft = run_agent_sync(agent.run(system_prompt)).output
    if draft is None:
        raise ValueError(f"email opener returned no draft for {deal.lead.public_identifier}")
    return draft
