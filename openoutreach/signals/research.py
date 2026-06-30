"""
AI-powered opportunity research for a nonprofit organization.

Public API:
  research_project(project)      → runs LLM research + imports results
  import_research_data(data, project=None) → imports a parsed research dict
"""
from __future__ import annotations

import json
import logging
from datetime import date

logger = logging.getLogger(__name__)

# ── Research prompt ──────────────────────────────────────────────────────────

_RESEARCH_PROMPT = """You are a nonprofit opportunity researcher for Anansi Atlas.

Research the nonprofit organization described below and identify real, verifiable funders, strategic partners, government entities, resource providers, and open grant opportunities aligned to their mission.

OUTPUT RULES:
- Return ONLY a valid JSON object. No markdown fences, no prose, no commentary.
- Every funder and opportunity MUST have at least one real source_url.
- Do not invent funders, grants, or deadlines. If you cannot verify something, omit it.
- Prioritize local and regional opportunities over national ones.
- Aim for: 5-10 funders, 3-5 partners, 2-4 government entities, 2-3 resource providers, 5-10 opportunities.

CHOICE VALUES (use exactly these strings):
funder_type: community_foundation | corporate_foundation | family_foundation | federal_government | state_government | local_government | united_way | workforce_board | other
partner_type: nonprofit | university_college | community_college | workforce_board | local_government_agency | public_library | school_district | healthcare_organization | corporate_partner | foundation | faith_based_organization | community_based_organization | other
entity_type: city_government | county_government | workforce_development_board | economic_development_agency | public_school_district | public_library | housing_community_development_agency | regional_planning_agency | other
resource_type: technical_assistance_provider | capacity_building_organization | nonprofit_support_center | volunteer_network | americorps_national_service | university_program | software_donation_program | shared_services_provider | equipment_assistance_program | broadband_digital_access_program | other
opportunity_type: grant | contract | partnership | resource | sponsorship | training | capacity_building
source_type: funder | government | resource_provider | partner | manual
priority_level: high | medium | low
status: active | upcoming | monitoring
verification_status: always use "unverified"

ORGANIZATION PROFILE:
{org_profile}

OUTPUT FORMAT (return this exact structure, fully populated):
{{
  "_schema_version": "1.0",
  "organization": {{"name": "", "mission": "", "geography": [], "focus_areas": []}},
  "researched_at": "{today}",
  "researcher": "anansi-atlas-ai",
  "funders": [
    {{"name": "", "funder_type": "", "geography": [], "focus_areas": [], "beneficiaries": [], "eligibility_notes": "", "website": "", "notes": "", "source_urls": [], "source_references": [], "source_notes": "", "verification_status": "unverified"}}
  ],
  "partners": [
    {{"name": "", "partner_type": "", "geography": [], "focus_areas": [], "beneficiaries": [], "collaboration_opportunities": [], "website": "", "notes": "", "mission_alignment_notes": "", "opportunity_notes": "", "source_urls": [], "source_references": [], "verification_status": "unverified"}}
  ],
  "government_entities": [
    {{"name": "", "entity_type": "", "geography": [], "focus_areas": [], "department_or_office": "", "opportunity_lanes": [], "website": "", "notes": ""}}
  ],
  "resource_providers": [
    {{"name": "", "resource_type": "", "geography": [], "focus_areas": [], "resource_categories": [], "eligibility_notes": "", "website": "", "notes": ""}}
  ],
  "opportunities": [
    {{"name": "", "opportunity_type": "", "source_type": "", "source_name": "", "geography": [], "focus_areas": [], "beneficiaries": [], "eligibility_notes": "", "funding_amount": null, "posted_date": null, "deadline": null, "priority_level": "", "status": "", "notes": "", "source_urls": [], "source_references": [], "source_notes": "", "verification_status": "unverified"}}
  ]
}}"""


def _build_org_profile(project) -> str:
    """Build a plain-text org profile from project data for the LLM prompt."""
    org = project.organization
    lines = [
        f"Organization: {org.name}",
        f"Mission: {org.mission or 'Not provided'}",
    ]
    if org.geography:
        lines.append(f"Geography: {', '.join(org.geography) if isinstance(org.geography, list) else org.geography}")
    if org.focus_areas:
        lines.append(f"Focus areas: {', '.join(org.focus_areas) if isinstance(org.focus_areas, list) else org.focus_areas}")
    if org.beneficiaries:
        lines.append(f"Beneficiaries: {', '.join(org.beneficiaries) if isinstance(org.beneficiaries, list) else org.beneficiaries}")
    if getattr(org, 'programs', None):
        lines.append(f"Programs: {org.programs}")
    if getattr(org, 'annual_budget', None):
        lines.append(f"Annual budget: {org.annual_budget}")
    if getattr(org, 'website', None):
        lines.append(f"Website: {org.website}")
    if project.intake_notes:
        lines.append(f"Additional context: {project.intake_notes}")
    return "\n".join(lines)


def research_project(project) -> dict:
    """
    Run AI-powered opportunity research for a project.

    Calls the configured LLM with a research prompt built from the project's
    organization profile, parses the JSON response, imports the results into
    the database, and returns a summary dict.

    Raises ValueError if LLM is not configured.
    Raises RuntimeError if the LLM returns unparseable JSON.
    """
    from pydantic_ai import Agent

    from openoutreach.core.llm import get_llm_model, run_agent_sync

    org_profile = _build_org_profile(project)
    today = date.today().isoformat()
    prompt = _RESEARCH_PROMPT.format(org_profile=org_profile, today=today)

    logger.info("Running AI research for project %s (%s)", project.pk, project.organization.name)

    agent = Agent(
        get_llm_model(),
        model_settings={"temperature": 0.1, "timeout": 120},
    )
    raw = run_agent_sync(agent.run(prompt)).output

    # Strip any accidental markdown fences
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error("LLM returned invalid JSON for project %s: %s", project.pk, e)
        raise RuntimeError(f"LLM returned unparseable JSON: {e}") from e

    summary = import_research_data(data, project=project)

    # Invalidate cached snapshot narratives so they regenerate with new data
    try:
        from openoutreach.signals.narratives import invalidate_cache
        invalidate_cache(project)
    except Exception:
        pass

    logger.info("Research complete for project %s: %s", project.pk, summary)
    return summary


def import_research_data(data: dict, project=None) -> dict:
    """
    Import a parsed Hermes/AI research dict into the database.

    Safe to call multiple times — uses update_or_create, never duplicates.
    Returns a summary dict of counts.
    """
    from openoutreach.funding.models import (
        Funder,
        GovernmentEntity,
        Opportunity,
        PartnerOrganization,
        ResourceProvider,
    )
    from openoutreach.funding.grounding import is_reserved_domain

    def _candidate_url(item):
        urls = item.get("source_urls") or []
        return (item.get("website") or (urls[0] if urls else "")).strip()

    def _passes_gate(item):
        """Grounding gate: reject anything with no source URL or a reserved/fake
        domain (the `.example.com` hallucination signature). Fast, no network."""
        url = _candidate_url(item)
        return bool(url) and not is_reserved_domain(url)

    counts = {"funders": 0, "partners": 0, "government": 0, "resources": 0, "opportunities": 0, "rejected": 0}

    for item in data.get("funders", []):
        name = item.get("name", "").strip()
        if not name:
            continue
        if not _passes_gate(item):
            counts["rejected"] += 1
            continue
        Funder.objects.update_or_create(
            name=name,
            defaults={
                "funder_type": _coerce(item.get("funder_type", ""), Funder.FunderType, Funder.FunderType.OTHER),
                "geography": item.get("geography", []),
                "focus_areas": item.get("focus_areas", []),
                "beneficiaries": item.get("beneficiaries", []),
                "eligibility_notes": item.get("eligibility_notes", ""),
                "website": item.get("website", ""),
                "notes": item.get("notes", ""),
                "source_urls": item.get("source_urls", []),
                "source_references": item.get("source_references", []),
                "source_notes": item.get("source_notes", ""),
                "verification_status": _coerce(item.get("verification_status", ""), Funder.VerificationStatus, Funder.VerificationStatus.UNVERIFIED),
                "intelligence_status": Funder.IntelligenceStatus.ACTIVE,
                "active": True,
            },
        )
        counts["funders"] += 1

    for item in data.get("partners", []):
        name = item.get("name", "").strip()
        if not name:
            continue
        if not _passes_gate(item):
            counts["rejected"] += 1
            continue
        PartnerOrganization.objects.update_or_create(
            name=name,
            defaults={
                "partner_type": _coerce(item.get("partner_type", ""), PartnerOrganization.PartnerType, PartnerOrganization.PartnerType.OTHER),
                "geography": item.get("geography", []),
                "focus_areas": item.get("focus_areas", []),
                "beneficiaries": item.get("beneficiaries", []),
                "collaboration_opportunities": item.get("collaboration_opportunities", []),
                "website": item.get("website", ""),
                "notes": item.get("notes", ""),
                "mission_alignment_notes": item.get("mission_alignment_notes", ""),
                "opportunity_notes": item.get("opportunity_notes", ""),
                "source_urls": item.get("source_urls", []),
                "source_references": item.get("source_references", []),
                "verification_status": _coerce(item.get("verification_status", ""), PartnerOrganization.VerificationStatus, PartnerOrganization.VerificationStatus.UNVERIFIED),
                "intelligence_status": PartnerOrganization.IntelligenceStatus.ACTIVE,
                "active": True,
            },
        )
        counts["partners"] += 1

    for item in data.get("government_entities", []):
        name = item.get("name", "").strip()
        if not name:
            continue
        if not _passes_gate(item):
            counts["rejected"] += 1
            continue
        GovernmentEntity.objects.update_or_create(
            name=name,
            defaults={
                "entity_type": _coerce(item.get("entity_type", ""), GovernmentEntity.EntityType, GovernmentEntity.EntityType.OTHER),
                "geography": item.get("geography", []),
                "focus_areas": item.get("focus_areas", []),
                "department_or_office": item.get("department_or_office", ""),
                "opportunity_lanes": item.get("opportunity_lanes", []),
                "website": item.get("website", ""),
                "notes": item.get("notes", ""),
                "active": True,
            },
        )
        counts["government"] += 1

    for item in data.get("resource_providers", []):
        name = item.get("name", "").strip()
        if not name:
            continue
        if not _passes_gate(item):
            counts["rejected"] += 1
            continue
        ResourceProvider.objects.update_or_create(
            name=name,
            defaults={
                "resource_type": _coerce(item.get("resource_type", ""), ResourceProvider.ResourceType, ResourceProvider.ResourceType.OTHER),
                "geography": item.get("geography", []),
                "focus_areas": item.get("focus_areas", []),
                "resource_categories": item.get("resource_categories", []),
                "eligibility_notes": item.get("eligibility_notes", ""),
                "website": item.get("website", ""),
                "notes": item.get("notes", ""),
                "active": True,
            },
        )
        counts["resources"] += 1

    for item in data.get("opportunities", []):
        name = item.get("name", "").strip()
        if not name:
            continue
        if not _passes_gate(item):
            counts["rejected"] += 1
            continue
        deadline = None
        if item.get("deadline"):
            try:
                deadline = date.fromisoformat(item["deadline"])
            except ValueError:
                pass
        posted_date = None
        if item.get("posted_date"):
            try:
                posted_date = date.fromisoformat(item["posted_date"])
            except ValueError:
                pass
        lookup = {"name": name}
        if project:
            lookup["project"] = project
        Opportunity.objects.update_or_create(
            **lookup,
            defaults={
                "opportunity_type": _coerce(item.get("opportunity_type", ""), Opportunity.OpportunityType, Opportunity.OpportunityType.GRANT),
                "source_type": _coerce(item.get("source_type", ""), Opportunity.SourceType, Opportunity.SourceType.MANUAL),
                "source_name": item.get("source_name", ""),
                "geography": item.get("geography", []),
                "focus_areas": item.get("focus_areas", []),
                "beneficiaries": item.get("beneficiaries", []),
                "eligibility_notes": item.get("eligibility_notes", ""),
                "funding_amount": item.get("funding_amount") or None,
                "deadline": deadline,
                "posted_date": posted_date,
                "priority_level": _coerce(item.get("priority_level", ""), Opportunity.PriorityLevel, Opportunity.PriorityLevel.MEDIUM),
                "status": _coerce(item.get("status", ""), Opportunity.Status, Opportunity.Status.ACTIVE),
                "lifecycle_status": Opportunity.LifecycleStatus.DISCOVERED,
                "notes": item.get("notes", ""),
                "source_urls": item.get("source_urls", []),
                "source_references": item.get("source_references", []),
                "source_notes": item.get("source_notes", ""),
                "verification_status": _coerce(item.get("verification_status", ""), Opportunity.VerificationStatus, Opportunity.VerificationStatus.UNVERIFIED),
            },
        )
        counts["opportunities"] += 1

    return counts


_FUNDER_RESEARCH_PROMPT = """You are a nonprofit funding researcher for Anansi Atlas.

Research the funder described below. Return ONLY a valid JSON object — no prose, no markdown.

Fill in as much accurate detail as you can verify. Do not invent data.

FUNDER:
Name: {name}
Type: {funder_type}
Website: {website}
Current notes: {notes}

Return this exact structure:
{{
  "focus_areas": [],
  "geography": [],
  "beneficiaries": [],
  "eligibility_notes": "",
  "typical_grant_range": "",
  "deadline_notes": "",
  "notes": "",
  "source_urls": []
}}"""


_SIGNUP_RESEARCH_PROMPT = """You are a nonprofit intelligence researcher for Anansi Atlas.

Research the organization below and return a brief intelligence summary. Return ONLY a valid JSON object — no prose, no markdown. Do not invent data; omit fields you cannot verify.

ORGANIZATION:
Name: {org_name}
Website: {website}
Contact role: {role}

Return this exact structure:
{{
  "org_type": "",
  "irs_status": "",
  "est_budget_range": "",
  "focus_areas": [],
  "geography": [],
  "existing_funders": [],
  "prior_grants_notes": "",
  "fit_notes": "",
  "source_urls": []
}}"""


def research_funder(funder) -> dict:
    """
    Run AI-powered research on a single Funder record and update its fields.

    Returns a dict of what was updated.
    """
    from pydantic_ai import Agent
    from openoutreach.core.llm import get_llm_model, run_agent_sync

    prompt = _FUNDER_RESEARCH_PROMPT.format(
        name=funder.name,
        funder_type=funder.funder_type,
        website=funder.website or "unknown",
        notes=funder.notes or "none",
    )
    logger.info("Running funder research for %s (pk=%s)", funder.name, funder.pk)
    agent = Agent(get_llm_model(), model_settings={"temperature": 0.1, "timeout": 60})
    raw = run_agent_sync(agent.run(prompt)).output

    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"LLM returned unparseable JSON for funder {funder.pk}: {e}") from e

    update_fields = []
    if data.get("focus_areas") and not funder.focus_areas:
        funder.focus_areas = data["focus_areas"]
        update_fields.append("focus_areas")
    if data.get("geography") and not funder.geography:
        funder.geography = data["geography"]
        update_fields.append("geography")
    if data.get("beneficiaries") and not funder.beneficiaries:
        funder.beneficiaries = data["beneficiaries"]
        update_fields.append("beneficiaries")
    if data.get("source_urls"):
        existing = funder.source_urls or []
        merged = list({u for u in existing + data["source_urls"]})
        if merged != existing:
            funder.source_urls = merged
            update_fields.append("source_urls")

    notes_parts = [funder.notes or ""]
    if data.get("eligibility_notes"):
        notes_parts.append(f"Eligibility: {data['eligibility_notes']}")
    if data.get("typical_grant_range"):
        notes_parts.append(f"Typical grant: {data['typical_grant_range']}")
    if data.get("deadline_notes"):
        notes_parts.append(f"Deadlines: {data['deadline_notes']}")
    if data.get("notes"):
        notes_parts.append(data["notes"])
    new_notes = "\n\n".join(p for p in notes_parts if p).strip()
    if new_notes != (funder.notes or ""):
        funder.notes = new_notes
        update_fields.append("notes")

    from django.utils import timezone
    funder.last_reviewed_at = timezone.now()
    update_fields.append("last_reviewed_at")

    if update_fields:
        funder.save(update_fields=list(set(update_fields)))

    logger.info("Funder research complete for %s: updated %s", funder.name, update_fields)
    return {"funder": funder.name, "updated_fields": update_fields, "raw": data}


def research_signup(signup) -> dict:
    """
    Run AI-powered org intelligence lookup on a waitlist InterestSignup.

    Stores the result in signup.research_brief (JSONField).
    Returns the brief dict.
    """
    from pydantic_ai import Agent
    from openoutreach.core.llm import get_llm_model, run_agent_sync
    from datetime import date

    prompt = _SIGNUP_RESEARCH_PROMPT.format(
        org_name=signup.organization or "Unknown",
        website=signup.website or "unknown",
        role=signup.role or "unknown",
    )
    logger.info("Running signup research for %s / %s", signup.organization, signup.email)
    agent = Agent(get_llm_model(), model_settings={"temperature": 0.1, "timeout": 60})
    raw = run_agent_sync(agent.run(prompt)).output

    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()

    try:
        brief = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"LLM returned unparseable JSON for signup {signup.pk}: {e}") from e

    brief["researched_at"] = date.today().isoformat()
    signup.research_brief = brief
    signup.save(update_fields=["research_brief"])
    logger.info("Signup research complete for %s", signup.email)
    return brief


def _coerce(value, choices_class, default):
    if not value:
        return default
    normalized = str(value).lower().replace("-", "_").replace(" ", "_")
    for choice in choices_class:
        if choice.value.lower() == normalized or choice.name.lower() == normalized:
            return choice
    return default
