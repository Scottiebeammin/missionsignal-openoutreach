"""
LLM-powered narrative enhancement for Opportunity Web Snapshots.

The deterministic pipeline in snapshot.py produces accurate structured data
(scores, factors, funder/partner/opportunity lists). This module takes that
output and enhances the narrative text fields — rationales, why_now,
preparation_required, mission_overview — with LLM-generated copy that is
specific to the organization.

One LLM call per snapshot. Results cached 24 hours in Django's cache
framework. Cache is invalidated when research runs (call invalidate_cache).

Public API:
  enhance_snapshot(project, snapshot) -> snapshot (mutated in place)
  invalidate_cache(project)
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict

logger = logging.getLogger(__name__)

_CACHE_TTL = 86_400  # 24 hours


def _cache_key(project) -> str:
    return f"snapshot_narratives_v1_{project.pk}"


def invalidate_cache(project) -> None:
    from django.core.cache import cache
    cache.delete(_cache_key(project))


def enhance_snapshot(project, snapshot):
    """
    Enhance snapshot narrative fields with LLM-generated copy.

    Mutates the snapshot object in place and returns it.
    Falls back silently to the original text if the LLM call fails.
    """
    from django.core.cache import cache

    key = _cache_key(project)
    cached = cache.get(key)

    if cached:
        _apply_narratives(snapshot, cached)
        logger.debug("Snapshot narratives served from cache for project %s", project.pk)
        return snapshot

    try:
        narratives = _generate_narratives(project, snapshot)
        cache.set(key, narratives, _CACHE_TTL)
        _apply_narratives(snapshot, narratives)
        logger.info("Snapshot narratives generated via LLM for project %s", project.pk)
    except Exception as e:
        logger.warning("LLM narrative enhancement failed for project %s: %s", project.pk, e)

    return snapshot


# ── Prompt builder ────────────────────────────────────────────────────────────

def _build_prompt(project, snapshot) -> str:
    org = project.organization

    # Build funder list
    funders = []
    for f in snapshot.funder_fit_insights[:6]:
        funders.append(f"- {f.archetype} ({f.alignment_level}) — factors: {', '.join(f.source_indicators[:3])}")

    # Build partner list
    partners = []
    for p in snapshot.partner_fit_insights[:4]:
        partners.append(f"- {p.name} ({p.partner_type})")

    # Build opportunity list
    opportunities = []
    for o in snapshot.top_opportunity_insights[:5]:
        parts = [f"- {o.name} (score {o.score}, {o.priority} priority)"]
        if o.factors:
            parts.append(f"  factors: {', '.join(o.factors[:3])}")
        opportunities.append("\n".join(parts))

    # Build action list
    actions = [f"- {a.label}: {a.rationale[:80]}" for a in snapshot.recommended_action_insights[:5]]

    # Build gap list
    gaps = [f"- {g.label}" for g in snapshot.ecosystem_gap_insights[:4]]

    # Build readiness list
    readiness_items = [f"- {r.label}" for r in snapshot.readiness_context_insights[:4]]

    prompt = f"""You are the voice of Anansi Atlas — a nonprofit opportunity intelligence platform.

Write clear, specific, encouraging narrative copy for the Opportunity Web Snapshot for the organization below.
Your writing should feel like a knowledgeable advisor who has studied this organization and is speaking directly to their leadership team.

TONE: Professional, warm, specific. Not generic. Not salesy. Use the org's actual mission, geography, and focus areas.
LENGTH: Each field should be 1-3 sentences. Concise and useful.

ORGANIZATION:
- Name: {org.name}
- Mission: {org.mission or "Not provided"}
- Geography: {', '.join(org.geography) if isinstance(org.geography, list) else org.geography or "Not provided"}
- Focus Areas: {', '.join(org.focus_areas) if isinstance(org.focus_areas, list) else org.focus_areas or "Not provided"}
- Beneficiaries: {', '.join(org.beneficiaries) if isinstance(org.beneficiaries, list) else org.beneficiaries or "Not provided"}
- Readiness Score: {snapshot.readiness_score}/100 ({snapshot.readiness_level})
- Programs: {getattr(org, 'programs', '') or "Not provided"}

TOP FUNDERS:
{chr(10).join(funders) or "None identified"}

TOP PARTNERS:
{chr(10).join(partners) or "None identified"}

TOP OPPORTUNITIES:
{chr(10).join(opportunities) or "None identified"}

RECOMMENDED ACTIONS:
{chr(10).join(actions) or "None identified"}

ECOSYSTEM GAPS:
{chr(10).join(gaps) or "None identified"}

READINESS CONTEXT:
{chr(10).join(readiness_items) or "None identified"}

OUTPUT: Return ONLY a valid JSON object with this exact structure. No markdown, no commentary:

{{
  "mission_overview": "<2-3 sentences: what this org does, who they serve, what makes them ready for this moment>",
  "funder_rationales": {{
    "<funder archetype exactly as listed above>": "<1-2 sentences: why this funder type aligns with their specific mission and geography>"
  }},
  "partner_rationales": {{
    "<partner name exactly as listed above>": "<1-2 sentences: what collaboration would look like and why it makes sense>"
  }},
  "opportunity_narratives": {{
    "<opportunity name exactly as listed above>": {{
      "rationale": "<1-2 sentences: why this opportunity is a strong fit>",
      "why_now": "<1 sentence: why timing matters or what makes this the right moment>",
      "preparation_required": "<1-2 sentences: what the org needs to do or strengthen before applying>",
      "risks": "<1 sentence: the main risk or gap to be aware of>"
    }}
  }},
  "action_rationales": {{
    "<action label exactly as listed above>": "<1-2 sentences: why this action moves the needle most right now>"
  }},
  "gap_rationales": {{
    "<gap label exactly as listed above>": "<1 sentence: what this gap costs the org in concrete terms>"
  }},
  "readiness_rationales": {{
    "<readiness item label exactly as listed above>": "<1-2 sentences: what this readiness issue means for their funding prospects>"
  }}
}}"""

    return prompt


# ── LLM call ─────────────────────────────────────────────────────────────────

def _generate_narratives(project, snapshot) -> dict:
    from pydantic_ai import Agent
    from openoutreach.core.llm import get_llm_model, run_agent_sync

    prompt = _build_prompt(project, snapshot)

    agent = Agent(
        get_llm_model(),
        model_settings={"temperature": 0.3, "timeout": 120},
    )
    raw = run_agent_sync(agent.run(prompt)).output

    # Strip markdown fences if present
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        if "```" in cleaned:
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()

    return json.loads(cleaned)


# ── Narrative injector ────────────────────────────────────────────────────────

def _apply_narratives(snapshot, narratives: dict) -> None:
    """Mutate snapshot fields in place with LLM-generated narratives."""

    if narratives.get("mission_overview"):
        snapshot.mission_overview = narratives["mission_overview"]

    funder_rationales = narratives.get("funder_rationales", {})
    for fit in snapshot.funder_fit_insights:
        text = funder_rationales.get(fit.archetype)
        if text:
            fit.rationale = text

    partner_rationales = narratives.get("partner_rationales", {})
    for fit in snapshot.partner_fit_insights:
        text = partner_rationales.get(fit.name)
        if text:
            fit.rationale = text

    opp_narratives = narratives.get("opportunity_narratives", {})
    for opp in snapshot.top_opportunity_insights:
        opp_data = opp_narratives.get(opp.name, {})
        if opp_data.get("rationale"):
            opp.rationale = opp_data["rationale"]
        if opp_data.get("why_now"):
            opp.why_now = opp_data["why_now"]
        if opp_data.get("preparation_required"):
            opp.preparation_required = opp_data["preparation_required"]
        if opp_data.get("risks"):
            opp.risks = opp_data["risks"]

    action_rationales = narratives.get("action_rationales", {})
    for action in snapshot.recommended_action_insights:
        text = action_rationales.get(action.label)
        if text:
            action.rationale = text

    gap_rationales = narratives.get("gap_rationales", {})
    for gap in snapshot.ecosystem_gap_insights:
        text = gap_rationales.get(gap.label)
        if text:
            gap.rationale = text

    readiness_rationales = narratives.get("readiness_rationales", {})
    for item in snapshot.readiness_context_insights:
        text = readiness_rationales.get(item.label)
        if text:
            item.rationale = text
