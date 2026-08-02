"""Map a real funder question onto what Atlas knows.

Answers exactly three questions, and keeps them apart on purpose:

- **Known by Atlas** — facts the organization supplied, read from real records.
  Only ``Fact`` objects from ``context_builder`` ever land here.
- **Needs Your Input** — information the question requires that Atlas does not
  hold, each with somewhere to go and supply it.
- **Suggested by Atlas** — writing and positioning advice. Never a fact, never
  a claim about the organization, and never allowed to cross into the first
  bucket. These are separate types (``Fact`` vs ``MissingFact`` vs
  ``Suggestion``), so the distinction is enforced by the data model rather than
  by remembering to be careful in a template.

Matching is deterministic: an imported question is free text, so it is scored
against a topic map of keywords. That keeps the mapping explainable ("this was
treated as a capacity question because it mentions staff and experience") and
means the whole screen works with no LLM configured.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from openoutreach.grants.models import GrantApplicationSection
from openoutreach.grants.services.context_builder import GrantContext, Fact, MissingFact, extract_numbers


@dataclass(frozen=True)
class Suggestion:
    """A writing recommendation. Deliberately NOT a Fact — it asserts nothing."""

    text: str
    reason: str = ""


@dataclass(frozen=True)
class LibraryMatch:
    """A previous approved answer worth adapting, with any freshness concerns."""

    item: object
    topic: str
    stale_numbers: list[str] = field(default_factory=list)
    age_note: str = ""

    @property
    def has_warning(self) -> bool:
        return bool(self.stale_numbers or self.age_note)


@dataclass
class QuestionAnalysis:
    known_facts: list[Fact] = field(default_factory=list)
    missing_information: list[MissingFact] = field(default_factory=list)
    writing_suggestions: list[Suggestion] = field(default_factory=list)
    relevant_answer_library_items: list[LibraryMatch] = field(default_factory=list)
    can_generate_draft: bool = False
    topics: list[str] = field(default_factory=list)
    gate_reason: str = ""

    @property
    def known_labels(self) -> list[str]:
        return [fact.label for fact in self.known_facts]

    @property
    def fact_keys(self) -> list[str]:
        return [fact.key for fact in self.known_facts]


# ── Topic map ────────────────────────────────────────────────────────────────
# Each topic ties question wording to the facts that answer it, the information
# requirements it depends on, and the advice worth giving. Adding a topic is a
# data change, not a code change.

@dataclass(frozen=True)
class Topic:
    key: str
    label: str
    keywords: tuple[str, ...]
    fact_keys: tuple[str, ...]
    requirements: tuple[str, ...] = ()
    library_categories: tuple[str, ...] = ()
    suggestions: tuple[str, ...] = ()


TOPICS: tuple[Topic, ...] = (
    Topic(
        "mission", "Mission",
        ("mission", "purpose", "why you exist", "vision", "values", "who you are"),
        ("organization.name", "organization.mission", "organization.summary",
         "organization.beneficiaries", "organization.focus_areas"),
        library_categories=("mission", "organization_overview"),
        suggestions=("State the mission in one sentence before adding context — most funders read only the first line closely.",),
    ),
    Topic(
        "history", "Organization history",
        ("history", "founded", "established", "how long", "background", "origin", "since"),
        ("organization.name", "organization.summary", "organization.year_founded",
         "organization.mission", "evidence.past_performance"),
        ("year_founded", "past_performance"),
        library_categories=("organization_history", "organization_overview"),
        suggestions=("Move quickly from founding story to current scale — funders care more about what you do now than how you began.",),
    ),
    Topic(
        "need", "Statement of need",
        ("need", "problem", "issue", "challenge", "gap", "why is this needed",
         "community need", "evidence of need", "conditions"),
        ("organization.beneficiaries", "organization.location", "organization.service_geographies",
         "organization.focus_areas", "evidence.community_need", "opportunity.focus_areas"),
        ("community_need_data", "service_area"),
        library_categories=("statement_of_need",),
        suggestions=(
            "Open with the specific community and the specific problem, not a national statistic.",
            "Cite one local, sourced figure — a claim a program officer can check is worth more than three they cannot.",
        ),
    ),
    Topic(
        "population", "Population served",
        ("who do you serve", "population", "participants", "beneficiaries", "clients",
         "demographic", "target audience", "serve", "reach", "how many people"),
        ("organization.beneficiaries", "organization.service_geographies", "organization.location",
         "evidence.people_served", "project.programs"),
        ("people_served_annually",),
        library_categories=("population_served",),
        suggestions=("Give a number and a description — 'youth' is a category, '412 middle-schoolers in Orange County' is an answer.",),
    ),
    Topic(
        "program", "Program description",
        ("program", "project", "activities", "services", "what will you do",
         "describe the project", "proposed", "initiative", "curriculum"),
        ("project.name", "project.programs", "project.program_summaries",
         "organization.capabilities", "organization.focus_areas",
         "opportunity.name", "opportunity.focus_areas"),
        library_categories=("program_description",),
        suggestions=("Describe what a participant actually experiences, step by step — funders fund activities, not adjectives.",),
    ),
    Topic(
        "goals", "Goals and objectives",
        ("goal", "objective", "aim", "target", "intend to achieve", "what will change",
         "expected result", "milestones"),
        ("project.programs", "organization.outcomes", "evidence.outcome_metrics",
         "opportunity.focus_areas"),
        ("measurable_outcomes",),
        library_categories=("goals", "outcomes"),
        suggestions=("Attach a number and a timeframe to each objective — an objective without either reads as a hope.",),
    ),
    Topic(
        "implementation", "Implementation and timeline",
        ("timeline", "implement", "schedule", "when will", "how will you carry",
         "work plan", "phases", "staffing plan"),
        ("project.programs", "organization.capabilities", "evidence.staffing",
         "opportunity.deadline", "documents.available"),
        ("staffing",),
        library_categories=("implementation_plan",),
        suggestions=("Name who is responsible for each activity — plans with owners read as real.",),
    ),
    Topic(
        "outcomes", "Outcomes and evaluation",
        ("outcome", "impact", "measure", "evaluate", "evaluation", "assess", "track",
         "data collection", "results", "success look like", "indicators"),
        ("organization.outcomes", "evidence.outcome_metrics", "evidence.evaluation",
         "project.programs"),
        ("measurable_outcomes", "evaluation_approach"),
        library_categories=("outcomes", "evaluation_approach"),
        suggestions=(
            "Say what you measure, how you collect it, and how often — the method matters as much as the metric.",
            "Include at least one result you have already achieved, not only what you intend to achieve.",
        ),
    ),
    Topic(
        "capacity", "Organizational capacity",
        ("capacity", "qualified", "experience", "staff", "staffing", "personnel", "team",
         "leadership", "board", "governance", "why is your organization", "track record",
         "uniquely positioned", "infrastructure"),
        ("organization.capabilities", "organization.summary", "project.programs",
         "evidence.past_performance", "evidence.staffing", "evidence.leadership",
         "documents.available"),
        ("staffing", "leadership", "past_performance"),
        library_categories=("organizational_capacity", "past_performance"),
        suggestions=("Tie capacity to this specific program — general competence is less persuasive than having run this exact work before.",),
    ),
    Topic(
        "partnerships", "Partnerships",
        ("partner", "collaborat", "coalition", "referral", "work with other",
         "letters of support", "stakeholder"),
        ("organization.partnerships", "evidence.partner_letters", "project.programs"),
        ("partnerships",),
        library_categories=("partnerships",),
        suggestions=("Name each partner and what they contribute — unnamed 'community partners' carry no weight.",),
    ),
    Topic(
        "sustainability", "Sustainability",
        ("sustain", "after the grant", "ongoing funding", "future funding", "long-term",
         "continue", "diversif", "beyond this"),
        ("organization.funding_sources", "organization.partnerships",
         "evidence.sustainability", "organization.budget_range"),
        ("funding_history", "sustainability_plan"),
        library_categories=("sustainability",),
        suggestions=("Say plainly what continues if this grant is not renewed — funders prefer an honest plan to an optimistic one.",),
    ),
    Topic(
        "budget", "Budget and finances",
        ("budget", "cost", "expense", "financial", "amount requested", "funds will be used",
         "how will the funds", "line item", "personnel cost", "revenue", "match"),
        ("organization.budget_range", "organization.funding_sources",
         "opportunity.funding_amount", "application.requested_amount", "documents.budget"),
        ("operating_budget", "program_budget"),
        library_categories=("budget_narrative",),
        suggestions=("Explain what the money buys in the same categories the budget form uses, so the narrative and the numbers agree.",),
    ),
    Topic(
        "geography", "Service area",
        ("service area", "geograph", "where do you", "location", "county", "city",
         "region", "communities served", "operate in"),
        ("organization.location", "organization.service_geographies",
         "opportunity.geography"),
        ("service_area",),
        suggestions=("Name the county and communities explicitly — geography is often a hard eligibility screen.",),
    ),
    Topic(
        "equity", "Equity and inclusion",
        ("equity", "inclusion", "diversity", "dei", "underserved", "marginalized",
         "culturally", "access", "barriers", "bipoc", "lived experience"),
        ("organization.beneficiaries", "organization.mission", "organization.focus_areas",
         "organization.summary"),
        library_categories=("equity_inclusion", "community_engagement"),
        suggestions=("Ground this in how the program is actually designed and staffed, not in a statement of values.",),
    ),
)

_TOPICS_BY_KEY = {topic.key: topic for topic in TOPICS}

# Facts worth showing on almost any narrative question — identity context the
# writer will need regardless of topic.
_BASELINE_FACT_KEYS = ("organization.name", "organization.mission")

_WORD = re.compile(r"[a-z][a-z'-]+")


def _match_topics(question_text: str, limit: int = 3) -> list[Topic]:
    """Score the question against the topic map; return the best matches."""
    haystack = (question_text or "").casefold()
    if not haystack.strip():
        return []
    scored: list[tuple[int, Topic]] = []
    for topic in TOPICS:
        score = 0
        for keyword in topic.keywords:
            if keyword in haystack:
                # Multi-word phrases are stronger evidence than single words.
                score += 2 if " " in keyword else 1
        if score:
            scored.append((score, topic))
    scored.sort(key=lambda pair: (-pair[0], pair[1].key))
    return [topic for _score, topic in scored[:limit]]


# ── Staleness ────────────────────────────────────────────────────────────────

_STALE_AGE_DAYS = 365


def _staleness(item, context: GrantContext) -> tuple[list[str], str]:
    """Flag figures in an old answer that current Atlas data cannot support.

    Deliberately simple and therefore reliable: any number in the saved answer
    that does not appear anywhere in the current fact corpus is surfaced for a
    human to check. It does not try to understand what the number means.
    """
    stale = [
        number for number in dict.fromkeys(extract_numbers(item.answer))
        if number not in context.supported_numbers
    ]
    age_note = ""
    updated = getattr(item, "updated_at", None)
    if updated is not None:
        from django.utils import timezone
        age_days = (timezone.now() - updated).days
        if age_days > _STALE_AGE_DAYS:
            age_note = f"Approved {age_days // 365} year(s) ago — confirm it still describes your work."
    return stale, age_note


def _library_matches(section, context: GrantContext, topics: list[Topic], limit: int = 3) -> list[LibraryMatch]:
    from openoutreach.grants.services.answer_library import library_for

    categories: list[str] = []
    for topic in topics:
        categories.extend(topic.library_categories)
    if not categories:
        return []

    organization = section.application.project.organization
    items = (
        library_for(organization)
        .filter(category__in=list(dict.fromkeys(categories)))
        .exclude(source_section=section)[:limit]
    )
    matches = []
    for item in items:
        stale_numbers, age_note = _staleness(item, context)
        topic_label = next(
            (t.label for t in topics if item.category in t.library_categories), "Previous answer",
        )
        matches.append(LibraryMatch(
            item=item, topic=topic_label, stale_numbers=stale_numbers, age_note=age_note,
        ))
    return matches


# ── Suggestions ──────────────────────────────────────────────────────────────

def _build_suggestions(section, context: GrantContext, topics: list[Topic]) -> list[Suggestion]:
    """Writing advice only. Nothing here asserts a fact about the organization."""
    suggestions: list[Suggestion] = []

    for topic in topics:
        for text in topic.suggestions:
            suggestions.append(Suggestion(text, reason=f"{topic.label} question"))

    # Funder alignment — the opportunity's own stated priorities.
    focus = context.fact("opportunity.focus_areas")
    if focus:
        suggestions.append(Suggestion(
            f"Connect your answer to the funder's stated priority: {focus.value}.",
            reason="From the opportunity record",
        ))
    geography = context.fact("organization.service_geographies") or context.fact("organization.location")
    if geography:
        suggestions.append(Suggestion(
            f"Lead with your direct experience in {geography.value} — local specificity is what "
            "separates a strong answer from a generic one.",
            reason="From your organization profile",
        ))

    # Evidence advice, based on what the org actually has available.
    if context.fact("evidence.outcome_metrics"):
        suggestions.append(Suggestion(
            "Include one measurable result from your Evidence Library rather than describing the "
            "program in general terms.",
            reason="You have outcome metrics recorded",
        ))

    # Length advice, only when the funder set a limit.
    if section.character_limit and section.character_limit <= 1000:
        suggestions.append(Suggestion(
            f"This answer is capped at {section.character_limit:,} characters — lead with the "
            "conclusion and cut background.",
            reason="Funder limit",
        ))
    elif section.word_limit and section.word_limit <= 200:
        suggestions.append(Suggestion(
            f"This answer is capped at {section.word_limit:,} words — one idea per sentence.",
            reason="Funder limit",
        ))

    # De-duplicate while preserving order.
    seen: set[str] = set()
    unique = []
    for suggestion in suggestions:
        if suggestion.text not in seen:
            seen.add(suggestion.text)
            unique.append(suggestion)
    return unique[:6]


# ── Public entry point ───────────────────────────────────────────────────────

# A narrative answer needs at least this many supporting facts before Atlas will
# offer to draft it unprompted.
_MIN_FACTS_TO_DRAFT = 2


def analyze_question(section, context: GrantContext) -> QuestionAnalysis:
    """Map one question onto Atlas's knowledge, gaps, and advice.

    Works for imported questions and standard-template sections alike: template
    sections carry their own declared fact keys, imported ones are matched by
    wording.
    """
    from openoutreach.grants.services.template import spec_for

    analysis = QuestionAnalysis()
    question_text = section.asked_question

    spec = spec_for(section.section_key) if not section.is_imported else None
    if spec is not None:
        fact_keys = list(spec.fact_keys)
        requirement_keys = list(spec.requirements)
        analysis.topics = [section.title]
        topics: list[Topic] = []
    else:
        topics = _match_topics(f"{question_text}\n{section.instructions}")
        analysis.topics = [topic.label for topic in topics]
        fact_keys, requirement_keys = [], []
        for topic in topics:
            fact_keys.extend(topic.fact_keys)
            requirement_keys.extend(topic.requirements)
        fact_keys.extend(_BASELINE_FACT_KEYS)
        # Opportunity facts help tailor any narrative answer.
        fact_keys.extend(("opportunity.name", "opportunity.funder", "opportunity.focus_areas"))

    # KNOWN BY ATLAS — real facts only, straight from the context builder.
    analysis.known_facts = context.facts_for(list(dict.fromkeys(fact_keys)))

    # NEEDS YOUR INPUT — requirements this question depends on that are unmet.
    analysis.missing_information = context.missing_for(list(dict.fromkeys(requirement_keys)))

    # SUGGESTED BY ATLAS — advice, never facts.
    analysis.writing_suggestions = _build_suggestions(section, context, topics)

    analysis.relevant_answer_library_items = _library_matches(section, context, topics)

    analysis.can_generate_draft, analysis.gate_reason = _gate(section, analysis)
    return analysis


def _gate(section, analysis: QuestionAnalysis) -> tuple[bool, str]:
    """Decide whether Atlas has enough to offer a draft, and say why."""
    if not section.is_draftable_type:
        label = GrantApplicationSection.QuestionType(section.question_type).label
        return False, (
            f"This is a {label.lower()} field, not a narrative answer — fill it in directly "
            "rather than drafting prose."
        )
    if len(analysis.known_facts) < _MIN_FACTS_TO_DRAFT:
        return False, (
            "Atlas does not yet hold enough about your organization to draft this answer well."
        )
    if analysis.missing_information:
        # A draft is still allowed — it will carry visible placeholders.
        return True, (
            "Atlas can draft this, but the answer will contain placeholders until the missing "
            "information is supplied."
        )
    return True, "Atlas has what this question needs."
