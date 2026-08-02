"""Grant Coach — contextual review of a written answer.

Deliberately rule-based, not a second chatbot. Every finding here is derived
from something checkable: a figure that cannot be traced to organization data,
an unresolved information requirement, a geography the funder named that the
organization's profile does not cover, a limit that has been exceeded. That
means a finding can always be explained, and never invents a critique.

The unsupported-claim check is the enforcement half of the anti-fabrication
rule. The drafting prompt asks the model not to invent figures; this module
verifies it didn't — and catches figures a human typed in by hand too.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from openoutreach.grants.services.context_builder import GrantContext, extract_numbers
from openoutreach.grants.services.template import REQUIREMENTS

STRONG = "strong"
NEEDS_WORK = "needs_work"
MISSING_EVIDENCE = "missing_evidence"
POSSIBLE_MISMATCH = "possible_mismatch"
UNSUPPORTED_CLAIM = "unsupported_claim"

KIND_LABELS = {
    STRONG: "Strong",
    NEEDS_WORK: "Needs Work",
    MISSING_EVIDENCE: "Missing Evidence",
    POSSIBLE_MISMATCH: "Possible Mismatch",
    UNSUPPORTED_CLAIM: "Unsupported Claim",
}

# Order findings by how much they should worry the writer.
_KIND_RANK = {
    UNSUPPORTED_CLAIM: 0,
    MISSING_EVIDENCE: 1,
    POSSIBLE_MISMATCH: 2,
    NEEDS_WORK: 3,
    STRONG: 4,
}

# Below this a required narrative section is not really answered yet.
_THIN_RESPONSE_WORDS = 40


@dataclass(frozen=True)
class Finding:
    kind: str
    message: str

    @property
    def label(self) -> str:
        return KIND_LABELS.get(self.kind, self.kind)

    @property
    def rank(self) -> int:
        return _KIND_RANK.get(self.kind, 9)


@dataclass(frozen=True)
class SectionReview:
    findings: list[Finding]
    unsupported_numbers: list[str]
    information_needed_markers: list[str]

    @property
    def has_blocking_issue(self) -> bool:
        return any(
            finding.kind in {UNSUPPORTED_CLAIM, MISSING_EVIDENCE} for finding in self.findings
        )


_MARKER = re.compile(r"\[Information needed:([^\]]*)\]", re.IGNORECASE)
_WORD = re.compile(r"[a-z][a-z'-]{3,}")


def information_needed_markers(text: str) -> list[str]:
    return [match.strip() or "Unspecified" for match in _MARKER.findall(text or "")]


def unsupported_numbers(text: str, context: GrantContext) -> list[str]:
    """Figures in *text* that Atlas cannot trace back to organization data.

    A number counts as supported when it appears anywhere in the fact corpus the
    draft was built from. Numbers inside `[Information needed: …]` markers are
    ignored — those are the writer flagging a gap, not asserting a figure.
    """
    stripped = _MARKER.sub(" ", text or "")
    seen: list[str] = []
    for number in extract_numbers(stripped):
        if number in context.supported_numbers or number in seen:
            continue
        seen.append(number)
    return seen


def _tokens(value: str) -> set[str]:
    return set(_WORD.findall((value or "").casefold()))


def _fact_tokens(context: GrantContext, *keys) -> set[str]:
    tokens: set[str] = set()
    for key in keys:
        fact = context.fact(key)
        if fact:
            tokens |= _tokens(fact.value)
    return tokens


def review_section(section, context: GrantContext, spec) -> SectionReview:
    """Review one written answer against the facts behind it."""
    text = section.current_text
    findings: list[Finding] = []

    if not text.strip():
        return SectionReview(findings=[], unsupported_numbers=[], information_needed_markers=[])

    markers = information_needed_markers(text)
    unsupported = unsupported_numbers(text, context)

    if unsupported:
        shown = ", ".join(unsupported[:5])
        findings.append(Finding(
            UNSUPPORTED_CLAIM,
            f"This response contains {'a figure' if len(unsupported) == 1 else 'figures'} "
            f"Atlas cannot trace to your organization data ({shown}). Confirm the number and "
            "add it to your profile or Evidence Library, or remove it.",
        ))

    if markers:
        findings.append(Finding(
            NEEDS_WORK,
            (f"{len(markers)} placeholders still need filling: " if len(markers) != 1
             else "1 placeholder still needs filling: ")
            + "; ".join(markers[:3]),
        ))

    missing = context.missing_for(spec.requirements)
    for item in missing:
        findings.append(Finding(
            MISSING_EVIDENCE,
            f"{item.label} is not in Atlas yet. {item.hint}",
        ))

    # Geography: a funder that names a service area the organization's profile
    # does not cover is a real eligibility risk, not a style note.
    opportunity_geo = context.fact("opportunity.geography")
    org_geo = context.fact("organization.service_geographies") or context.fact("organization.location")
    if opportunity_geo and org_geo:
        geo_tokens = _tokens(opportunity_geo.value)
        org_geo_tokens = _tokens(org_geo.value)
        if geo_tokens and org_geo_tokens and not (geo_tokens & org_geo_tokens):
            findings.append(Finding(
                POSSIBLE_MISMATCH,
                f"This opportunity names {opportunity_geo.value}, but your profile lists "
                f"{org_geo.value} as your service area. Confirm you are eligible before submitting.",
            ))

    # Funder priority alignment — reported as strong when the response actually
    # speaks to it, and as a gap when it doesn't.
    opportunity_focus = context.fact("opportunity.focus_areas")
    if opportunity_focus:
        response_tokens = _tokens(text)
        focus_tokens = _tokens(opportunity_focus.value)
        overlap = focus_tokens & response_tokens
        if overlap:
            findings.append(Finding(
                STRONG,
                f"This response speaks to the funder's stated priority ({', '.join(sorted(overlap)[:3])}).",
            ))
        elif focus_tokens:
            findings.append(Finding(
                NEEDS_WORK,
                f"The funder emphasizes {opportunity_focus.value}. This response does not "
                "currently connect your work to that priority.",
            ))

    if section.over_character_limit:
        findings.append(Finding(
            NEEDS_WORK,
            f"This response is {section.character_count - section.character_limit:,} characters over "
            f"the {section.character_limit:,}-character limit. Use Shorten to bring it within range.",
        ))
    elif section.over_word_limit:
        findings.append(Finding(
            NEEDS_WORK,
            f"This response is {section.word_count - section.word_limit:,} words over the "
            f"{section.word_limit:,}-word limit. Use Shorten to bring it within range.",
        ))

    if spec.required and section.word_count < _THIN_RESPONSE_WORDS and not markers:
        findings.append(Finding(
            NEEDS_WORK,
            "This response is short for a required section. Reviewers usually expect the "
            "full picture here.",
        ))

    findings.sort(key=lambda finding: finding.rank)
    return SectionReview(
        findings=findings,
        unsupported_numbers=unsupported,
        information_needed_markers=markers,
    )


def requirement_label(key: str) -> str:
    spec = REQUIREMENTS.get(key)
    return spec.label if spec else key


# ── Imported-question review ─────────────────────────────────────────────────
# A real funder question deserves a different read than a template section: the
# first thing that matters is whether the answer actually answers what was
# asked. Five dimensions, each reported as a LABEL with an explanation and one
# concrete improvement — no invented percentage scores.

STRONG_LABEL = "Strong"
MODERATE_LABEL = "Moderate"
NEEDS_ATTENTION_LABEL = "Needs Attention"
INCOMPLETE_LABEL = "Incomplete"

_LABEL_RANK = {
    INCOMPLETE_LABEL: 0,
    NEEDS_ATTENTION_LABEL: 1,
    MODERATE_LABEL: 2,
    STRONG_LABEL: 3,
}

# Words that fill space without saying anything checkable.
_VAGUE_TERMS = (
    "various", "numerous", "many", "several", "significant", "substantial",
    "world-class", "cutting-edge", "innovative", "passionate", "committed to excellence",
    "best-in-class", "leading", "premier", "robust", "synergy", "holistic",
    "a wide range", "state-of-the-art", "meaningful impact", "make a difference",
)

# Question words carry no information about the answer's content.
_STOPWORDS = frozenset({
    "describe", "explain", "provide", "please", "your", "you", "the", "and", "for",
    "with", "that", "this", "will", "what", "how", "why", "who", "organization",
    "organisation", "include", "should", "would", "which", "their", "there",
    "about", "from", "into", "have", "has", "does", "list", "state", "detail",
    "summarize", "summarise", "outline", "discuss", "identify", "any", "all",
})


@dataclass(frozen=True)
class Dimension:
    name: str
    label: str
    explanation: str
    improvement: str = ""

    @property
    def rank(self) -> int:
        return _LABEL_RANK.get(self.label, 0)


@dataclass(frozen=True)
class ImportedQuestionReview:
    dimensions: list[Dimension]
    unsupported_numbers: list[str]
    information_needed_markers: list[str]

    @property
    def overall_label(self) -> str:
        """The weakest dimension — an answer is only as good as its worst part."""
        if not self.dimensions:
            return INCOMPLETE_LABEL
        return min(self.dimensions, key=lambda d: d.rank).label

    @property
    def needs_work(self) -> list[Dimension]:
        return [d for d in self.dimensions if d.label != STRONG_LABEL]


def _content_words(text: str) -> set[str]:
    return {
        word for word in _WORD.findall((text or "").casefold())
        if word not in _STOPWORDS and len(word) > 3
    }


def _dimension_answered(section, text: str) -> Dimension:
    """Does the response engage the terms the funder actually used?"""
    asked = _content_words(section.asked_question)
    answered = _content_words(text)
    if not asked:
        return Dimension(
            "Answered the Question", MODERATE_LABEL,
            "Atlas could not read distinctive terms from the question, so this could not be checked.",
            "Re-read the funder's question and confirm the response addresses it directly.",
        )
    overlap = asked & answered
    ratio = len(overlap) / len(asked)
    if ratio >= 0.5:
        return Dimension(
            "Answered the Question", STRONG_LABEL,
            f"The response engages the terms the funder used ({', '.join(sorted(overlap)[:4])}).",
        )
    if ratio >= 0.25:
        missed = sorted(asked - answered)[:4]
        return Dimension(
            "Answered the Question", MODERATE_LABEL,
            "The response is on topic but does not pick up every part of the question.",
            f"Address these explicitly: {', '.join(missed)}.",
        )
    missed = sorted(asked - answered)[:5]
    return Dimension(
        "Answered the Question", NEEDS_ATTENTION_LABEL,
        "The response does not clearly answer what this question asked.",
        f"The funder asked about {', '.join(missed)} — answer that directly, in the first sentence.",
    )


def _dimension_evidence(text: str, unsupported: list[str], supported_hits: int) -> Dimension:
    if unsupported:
        return Dimension(
            "Evidence", NEEDS_ATTENTION_LABEL,
            f"Contains {'a figure' if len(unsupported) == 1 else 'figures'} Atlas cannot trace to "
            f"your organization data ({', '.join(unsupported[:4])}).",
            "Add the figure to your profile or Evidence Library so it is supported, or remove it.",
        )
    if supported_hits >= 2:
        return Dimension(
            "Evidence", STRONG_LABEL,
            "Factual claims are backed by figures already recorded in Atlas.",
        )
    if supported_hits == 1:
        return Dimension(
            "Evidence", MODERATE_LABEL,
            "One supported figure appears in the response.",
            "Add a second concrete result — reviewers weigh evidence more than description.",
        )
    return Dimension(
        "Evidence", NEEDS_ATTENTION_LABEL,
        "The response makes no measurable claim.",
        "Include at least one figure from your Evidence Library.",
    )


def _dimension_specificity(text: str) -> Dimension:
    lowered = (text or "").casefold()
    vague_hits = [term for term in _VAGUE_TERMS if term in lowered]
    has_numbers = bool(extract_numbers(text))
    if len(vague_hits) >= 3:
        return Dimension(
            "Specificity", NEEDS_ATTENTION_LABEL,
            f"Leans on vague language ({', '.join(vague_hits[:3])}).",
            "Replace each with a concrete detail: who, where, how many.",
        )
    if vague_hits and not has_numbers:
        return Dimension(
            "Specificity", MODERATE_LABEL,
            f"Some general phrasing ({vague_hits[0]}) and no concrete figures.",
            "Swap the general claim for a specific one a reader could verify.",
        )
    if has_numbers:
        return Dimension("Specificity", STRONG_LABEL, "Uses concrete, checkable detail.")
    return Dimension(
        "Specificity", MODERATE_LABEL,
        "Reads clearly but stays general.",
        "Name the place, the population, or the number.",
    )


def _dimension_alignment(context: GrantContext, text: str) -> Dimension:
    focus = context.fact("opportunity.focus_areas")
    if not focus:
        return Dimension(
            "Funder Alignment", MODERATE_LABEL,
            "The opportunity record does not list focus areas, so alignment could not be checked.",
            "Check the funder's published priorities and reflect them here.",
        )
    overlap = _tokens(focus.value) & _tokens(text)
    if overlap:
        return Dimension(
            "Funder Alignment", STRONG_LABEL,
            f"Connects to the funder's stated priority ({', '.join(sorted(overlap)[:3])}).",
        )
    return Dimension(
        "Funder Alignment", NEEDS_ATTENTION_LABEL,
        f"This funder emphasises {focus.value}, which the response does not mention.",
        "Draw an explicit line from your work to that priority.",
    )


def _dimension_readability(text: str, section) -> Dimension:
    sentences = [s for s in re.split(r"[.!?]+", text or "") if s.strip()]
    if not sentences:
        return Dimension("Readability", INCOMPLETE_LABEL, "There is nothing written yet.")
    longest = max(len(s.split()) for s in sentences)
    average = sum(len(s.split()) for s in sentences) / len(sentences)
    if section.over_limit:
        return Dimension(
            "Readability", NEEDS_ATTENTION_LABEL,
            "The response is over the funder's limit.",
            "Use Shorten to bring it within range without dropping facts.",
        )
    if average > 32 or longest > 55:
        return Dimension(
            "Readability", NEEDS_ATTENTION_LABEL,
            f"Sentences run long (longest is {longest} words).",
            "Split the longest sentences — reviewers skim.",
        )
    if average > 24:
        return Dimension(
            "Readability", MODERATE_LABEL,
            "Somewhat dense, but readable.",
            "Trim the longest sentences for a faster read.",
        )
    return Dimension("Readability", STRONG_LABEL, "Clear and easy to read at review speed.")


def review_imported_question(section, context: GrantContext, analysis=None) -> ImportedQuestionReview:
    """Five-dimension review of an answer to a real funder question."""
    text = section.current_text
    markers = information_needed_markers(text)
    unsupported = unsupported_numbers(text, context)

    if not text.strip():
        return ImportedQuestionReview(
            dimensions=[Dimension(
                "Answered the Question", INCOMPLETE_LABEL, "No response has been written yet.",
                "Generate a draft or write the answer directly.",
            )],
            unsupported_numbers=[],
            information_needed_markers=[],
        )

    stripped = _MARKER.sub(" ", text)
    supported_hits = sum(
        1 for number in dict.fromkeys(extract_numbers(stripped))
        if number in context.supported_numbers
    )

    dimensions = [
        _dimension_answered(section, text),
        _dimension_evidence(text, unsupported, supported_hits),
        _dimension_specificity(text),
        _dimension_alignment(context, text),
        _dimension_readability(text, section),
    ]
    if markers:
        dimensions.insert(0, Dimension(
            "Answered the Question", INCOMPLETE_LABEL,
            f"{len(markers)} placeholder{'s' if len(markers) != 1 else ''} still to fill: "
            + "; ".join(markers[:3]),
            "Supply the missing information, then regenerate or edit the answer.",
        ))
    return ImportedQuestionReview(
        dimensions=dimensions,
        unsupported_numbers=unsupported,
        information_needed_markers=markers,
    )
