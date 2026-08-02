"""Gather everything Atlas already knows, once, in one place.

This is the single reuse boundary for Grant Builder: views, the drafting agent,
the coach, and the completeness review all read the same ``GrantContext``. No
page component reaches into ``Organization``/``Project``/``Evidence`` directly.

Two rules shape the design:

1. **A fact is only a fact if it came from the organization.** Every ``Fact``
   carries the human-readable label of where it came from, which becomes the
   "Sources Used" list in the UI and the only material the drafter may use.
2. **Absence is information.** A requirement that cannot be resolved is not
   quietly skipped — it becomes a ``MissingFact`` with a place to go fix it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from openoutreach.funding.models import DocumentVaultItem, EvidenceLibraryItem
from openoutreach.grants.services.template import REQUIREMENTS, RequirementSpec


@dataclass(frozen=True)
class Fact:
    key: str
    label: str
    value: str

    @property
    def is_present(self) -> bool:
        return bool(self.value.strip())


@dataclass(frozen=True)
class MissingFact:
    key: str
    label: str
    hint: str
    add_url_name: str
    add_label: str


@dataclass
class GrantContext:
    """Every organization/opportunity fact available to one grant application."""

    application: object
    project: object
    organization: object
    opportunity: object
    facts: dict[str, Fact] = field(default_factory=dict)
    resolved_requirements: dict[str, bool] = field(default_factory=dict)
    # Every number Atlas can legitimately support, used by the coach to spot
    # figures the AI (or a person) introduced from nowhere.
    supported_numbers: set[str] = field(default_factory=set)

    def fact(self, key: str) -> Fact | None:
        found = self.facts.get(key)
        return found if found and found.is_present else None

    def facts_for(self, keys) -> list[Fact]:
        return [fact for fact in (self.fact(key) for key in keys) if fact is not None]

    def available_labels(self, keys) -> list[str]:
        return [fact.label for fact in self.facts_for(keys)]

    def missing_for(self, requirement_keys) -> list[MissingFact]:
        missing = []
        for key in requirement_keys:
            if self.resolved_requirements.get(key):
                continue
            spec = REQUIREMENTS.get(key)
            if spec is None:
                continue
            missing.append(
                MissingFact(
                    key=spec.key,
                    label=spec.label,
                    hint=spec.hint,
                    add_url_name=spec.add_url_name,
                    add_label=spec.add_label,
                )
            )
        return missing

    @property
    def all_missing(self) -> list[MissingFact]:
        return self.missing_for(
            [key for key, resolved in self.resolved_requirements.items() if not resolved]
        )

    @property
    def requirement_coverage(self) -> int:
        """Share of Grant Builder's information requirements Atlas can satisfy."""
        if not self.resolved_requirements:
            return 0
        met = sum(1 for resolved in self.resolved_requirements.values() if resolved)
        return round((met / len(self.resolved_requirements)) * 100)


# ── Value formatting ─────────────────────────────────────────────────────────

def _text(value) -> str:
    return str(value or "").strip()


def _joined(values) -> str:
    if isinstance(values, str):
        return _text(values)
    if isinstance(values, dict):
        values = [f"{k}: {v}" for k, v in values.items()]
    return ", ".join(_text(item) for item in (values or []) if _text(item))


def _lines(values) -> str:
    return "\n".join(f"- {_text(item)}" for item in (values or []) if _text(item))


_YEAR_FOUNDED = re.compile(
    r"\b(?:founded|established|incorporated|since|serving\s+\w+\s+since)\D{0,20}(1[89]\d{2}|20\d{2})\b",
    re.IGNORECASE,
)


def _year_founded(*texts) -> str:
    for text in texts:
        match = _YEAR_FOUNDED.search(_text(text))
        if match:
            return match.group(1)
    return ""


# ── Evidence / document helpers ──────────────────────────────────────────────

_USABLE_EVIDENCE = (EvidenceLibraryItem.Status.AVAILABLE, EvidenceLibraryItem.Status.NEEDS_UPDATE)
_USABLE_DOCUMENTS = (DocumentVaultItem.Status.AVAILABLE, DocumentVaultItem.Status.NEEDS_UPDATE)

_PEOPLE_SERVED_TERMS = (
    "served", "serve", "participants", "reached", "clients", "students",
    "youth", "families", "enrolled", "attendance",
)
_STAFF_TERMS = ("staff", "fte", "employee", "personnel", "headcount", "team member")
_LEADERSHIP_TERMS = ("board", "leadership", "executive director", "trustee", "governance")
_SUSTAINABILITY_TERMS = ("sustainab", "strategic plan", "diversif", "earned revenue", "renewal")


def _evidence_text(item: EvidenceLibraryItem) -> str:
    metric = " ".join(part for part in (item.metric_name, item.metric_value) if part)
    parts = [item.title, item.related_program, metric, item.notes]
    return " · ".join(part.strip() for part in parts if (part or "").strip())


def _matching_evidence(items, terms) -> list[EvidenceLibraryItem]:
    return [
        item for item in items
        if any(term in _evidence_text(item).casefold() for term in terms)
    ]


def _matching_documents(items, terms) -> list[DocumentVaultItem]:
    return [
        item for item in items
        if any(term in f"{item.title} {item.notes}".casefold() for term in terms)
    ]


# ── Number extraction (grounding for the anti-fabrication check) ─────────────

_NUMBER_TOKEN = re.compile(r"\d[\d,]*(?:\.\d+)?")


def extract_numbers(text: str) -> list[str]:
    """Every numeric token in a blob, normalized (commas stripped, .0 dropped)."""
    found = []
    for raw in _NUMBER_TOKEN.findall(text or ""):
        cleaned = raw.replace(",", "").rstrip(".")
        if not cleaned:
            continue
        if cleaned.endswith(".0"):
            cleaned = cleaned[:-2]
        found.append(cleaned)
    return found


# ── Builder ──────────────────────────────────────────────────────────────────

def build_grant_context(application) -> GrantContext:
    """Assemble the full fact set for one grant application.

    Reads only records the application's project already owns — the same
    ownership boundary every other portal page uses.
    """
    project = application.project
    organization = project.organization
    opportunity = application.opportunity

    evidence = list(
        EvidenceLibraryItem.objects.filter(project=project, status__in=_USABLE_EVIDENCE)
    )
    documents = list(
        DocumentVaultItem.objects.filter(project=project, status__in=_USABLE_DOCUMENTS)
    )
    criteria = getattr(project, "funding_criteria", None)

    outcome_metrics = [item for item in evidence if item.metric_value.strip()]
    community_need = [
        item for item in evidence
        if item.evidence_type == EvidenceLibraryItem.EvidenceType.COMMUNITY_NEED_DATA
    ]
    evaluation = [
        item for item in evidence
        if item.evidence_type == EvidenceLibraryItem.EvidenceType.EVALUATION_REPORT
    ] + _matching_evidence(evidence, ("evaluat", "assessment", "pre/post", "survey"))
    past_performance = [
        item for item in evidence
        if item.evidence_type in {
            EvidenceLibraryItem.EvidenceType.PROGRAM_RESULT,
            EvidenceLibraryItem.EvidenceType.IMPACT_STORY,
            EvidenceLibraryItem.EvidenceType.OUTCOME_METRIC,
        }
    ]
    partner_letters = [
        item for item in evidence
        if item.evidence_type == EvidenceLibraryItem.EvidenceType.PARTNER_LETTER
    ]
    people_served = [
        item for item in outcome_metrics
        if any(term in _evidence_text(item).casefold() for term in _PEOPLE_SERVED_TERMS)
    ]
    staffing = _matching_evidence(evidence, _STAFF_TERMS)
    leadership_evidence = _matching_evidence(evidence, _LEADERSHIP_TERMS)
    leadership_documents = [
        item for item in documents
        if item.document_type in {
            DocumentVaultItem.DocumentType.BOARD_LIST,
            DocumentVaultItem.DocumentType.ANNUAL_REPORT,
        }
    ]
    sustainability = _matching_evidence(evidence, _SUSTAINABILITY_TERMS) + _matching_documents(
        documents, _SUSTAINABILITY_TERMS
    )
    budget_documents = [
        item for item in documents
        if item.document_type in {
            DocumentVaultItem.DocumentType.ANNUAL_BUDGET,
            DocumentVaultItem.DocumentType.PROGRAM_BUDGET,
            DocumentVaultItem.DocumentType.AUDIT_FINANCIAL_STATEMENT,
        }
    ]
    determination_letters = [
        item for item in documents
        if item.document_type == DocumentVaultItem.DocumentType.IRS_DETERMINATION_LETTER
    ]

    def _evidence_block(items) -> str:
        return _lines(_evidence_text(item) for item in items)

    location = ", ".join(
        part for part in (organization.city, organization.county, organization.state) if part
    )
    year_founded = _year_founded(organization.organization_summary, organization.mission)

    raw_facts: list[tuple[str, str, str]] = [
        ("organization.name", "Organization Name", _text(organization.name)),
        ("organization.mission", "Organization Mission", _text(organization.mission)),
        ("organization.summary", "Organization Summary", _text(organization.organization_summary)),
        ("organization.website", "Organization Website", _text(organization.website)),
        ("organization.type", "Organization Type", _joined(organization.organization_type)),
        ("organization.legal_structure", "Legal Structure", _joined(organization.legal_structure)),
        (
            "organization.nonprofit_status", "Nonprofit Status",
            _joined(organization.nonprofit_status)
            or (", ".join(item.title for item in determination_letters)),
        ),
        ("organization.location", "Headquarters Location", location),
        (
            "organization.service_geographies", "Service Area",
            _joined(organization.service_geographies) or _text(organization.service_area_notes),
        ),
        ("organization.focus_areas", "Focus Areas", _joined(organization.focus_areas)),
        ("organization.beneficiaries", "Population Served", _joined(organization.beneficiaries)),
        ("organization.capabilities", "Organizational Capabilities", _joined(organization.capabilities)),
        ("organization.outcomes", "Outcomes and Impact", _lines(organization.outcomes_and_impact)),
        ("organization.partnerships", "Existing Partnerships", _joined(organization.existing_partnerships)),
        ("organization.funding_sources", "Current Funding Sources", _joined(organization.current_funding_sources)),
        ("organization.budget_range", "Annual Budget Range", _text(organization.budget_range)),
        ("organization.year_founded", "Year Founded", year_founded),

        ("project.name", "Project Name", _text(project.name)),
        ("project.programs", "Primary Programs", _text(project.programs)),
        ("project.program_summaries", "Program Summaries", _lines(project.program_summaries)),
        ("project.intake_notes", "Intake Notes", _text(project.intake_notes)),

        ("criteria.program_areas", "Program Areas", _joined(getattr(criteria, "program_areas", []))),
        (
            "criteria.funding_use", "Funding Use Categories",
            _joined(getattr(criteria, "funding_use_categories", [])),
        ),

        ("evidence.outcome_metrics", "Outcome Metrics (Evidence Library)", _evidence_block(outcome_metrics)),
        ("evidence.people_served", "People Served (Evidence Library)", _evidence_block(people_served)),
        ("evidence.community_need", "Community Need Data (Evidence Library)", _evidence_block(community_need)),
        ("evidence.evaluation", "Evaluation Evidence", _evidence_block(evaluation)),
        ("evidence.past_performance", "Past Performance (Evidence Library)", _evidence_block(past_performance)),
        ("evidence.partner_letters", "Partner Letters", _evidence_block(partner_letters)),
        ("evidence.staffing", "Staffing Evidence", _evidence_block(staffing)),
        (
            "evidence.leadership", "Leadership and Board",
            _evidence_block(leadership_evidence) or _lines(item.title for item in leadership_documents),
        ),
        ("evidence.sustainability", "Sustainability Evidence", _evidence_block(sustainability)),

        ("documents.available", "Document Vault", _lines(item.title for item in documents)),
        ("documents.budget", "Budget Documents", _lines(item.title for item in budget_documents)),

        ("opportunity.name", "Opportunity Name", _text(opportunity.name)),
        (
            "opportunity.funder", "Funder",
            _text(application.funder_name) or _text(opportunity.source_name),
        ),
        ("opportunity.focus_areas", "Opportunity Focus Areas", _joined(opportunity.focus_areas)),
        ("opportunity.beneficiaries", "Opportunity Target Population", _joined(opportunity.beneficiaries)),
        ("opportunity.geography", "Opportunity Geography", _joined(opportunity.geography)),
        ("opportunity.eligibility_notes", "Opportunity Eligibility", _text(opportunity.eligibility_notes)),
        (
            "opportunity.applicant_types", "Eligible Applicant Types",
            _joined([
                entry.get("description", "") if isinstance(entry, dict) else entry
                for entry in (opportunity.applicant_types or [])
            ]),
        ),
        (
            "opportunity.funding_amount", "Opportunity Funding Amount",
            f"${opportunity.funding_amount:,.0f}" if opportunity.funding_amount else "",
        ),
        (
            "opportunity.deadline", "Opportunity Deadline",
            application.deadline.isoformat() if application.deadline else "",
        ),
        ("opportunity.notes", "Opportunity Notes", _text(opportunity.notes)),
        (
            "application.requested_amount", "Requested Amount",
            f"${application.requested_amount:,.0f}" if application.requested_amount else "",
        ),
    ]

    facts = {
        key: Fact(key=key, label=label, value=value)
        for key, label, value in raw_facts
        if _text(value)
    }

    resolved = {
        "nonprofit_status": bool(facts.get("organization.nonprofit_status")),
        "service_area": bool(
            facts.get("organization.service_geographies") or facts.get("organization.location")
        ),
        "year_founded": bool(year_founded),
        "past_performance": bool(past_performance),
        "community_need_data": bool(community_need),
        "people_served_annually": bool(people_served),
        # "Two measurable outcomes" is a real bar, not a vibe: either the org
        # recorded outcomes on its profile, or the Evidence Library holds at
        # least two metrics that actually carry a value.
        "measurable_outcomes": len(outcome_metrics) >= 2 or bool(organization.outcomes_and_impact),
        "evaluation_approach": bool(evaluation),
        "staffing": bool(staffing),
        "leadership": bool(leadership_evidence or leadership_documents),
        "partnerships": bool(organization.existing_partnerships or partner_letters),
        "funding_history": bool(organization.current_funding_sources),
        "sustainability_plan": bool(sustainability),
        "operating_budget": bool(_text(organization.budget_range)),
        "program_budget": bool(budget_documents),
    }

    supported_numbers: set[str] = set()
    for fact in facts.values():
        supported_numbers.update(extract_numbers(fact.value))

    return GrantContext(
        application=application,
        project=project,
        organization=organization,
        opportunity=opportunity,
        facts=facts,
        resolved_requirements=resolved,
        supported_numbers=supported_numbers,
    )


def requirement_spec(key: str) -> RequirementSpec | None:
    return REQUIREMENTS.get(key)


def render_facts_block(context: GrantContext, keys) -> str:
    """Render the labeled facts the drafter is allowed to use, and nothing else."""
    blocks = []
    for fact in context.facts_for(keys):
        blocks.append(f"{fact.label}:\n{fact.value}")
    return "\n\n".join(blocks) if blocks else "(No organization facts are available for this section.)"
