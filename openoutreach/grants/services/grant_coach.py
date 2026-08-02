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
