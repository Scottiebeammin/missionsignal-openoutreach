"""Application review — what stands between this draft and submission.

Every number on this screen is derived from a countable fact (approved sections,
resolved information requirements, evidence rows with a value). Where a real
score cannot be computed, Grant Builder reports a LABEL — Strong / Moderate /
Needs Attention / Incomplete — instead of inventing decimal precision. A made-up
89% would be exactly the kind of unearned confidence this feature exists to
remove from grant writing.
"""
from __future__ import annotations

from dataclasses import dataclass

from openoutreach.grants.models import GrantApplicationSection
from openoutreach.grants.services import grant_coach
from openoutreach.grants.services.context_builder import GrantContext
from openoutreach.grants.services.template import spec_for

STRONG = "Strong"
MODERATE = "Moderate"
NEEDS_ATTENTION = "Needs Attention"
INCOMPLETE = "Incomplete"


@dataclass(frozen=True)
class Metric:
    """One review metric. ``score`` is None when only a label is honest."""

    label: str
    value: str
    score: int | None
    basis: str


@dataclass(frozen=True)
class Issue:
    section_title: str
    message: str
    section_key: str = ""


@dataclass(frozen=True)
class ApplicationReview:
    completion_percent: int
    metrics: list[Metric]
    issues: list[Issue]
    approved_sections: int
    required_sections: int
    draftable_sections: int
    blocked_sections: int

    @property
    def issue_count(self) -> int:
        return len(self.issues)

    @property
    def is_submission_ready(self) -> bool:
        return not self.issues and self.completion_percent >= 100


def _label_for(ratio: float) -> str:
    if ratio >= 0.85:
        return STRONG
    if ratio >= 0.6:
        return MODERATE
    if ratio > 0:
        return NEEDS_ATTENTION
    return INCOMPLETE


def _alignment_metric(context: GrantContext) -> Metric:
    """Funder alignment, counted over the three dimensions Atlas can actually check."""
    checks = (
        ("focus area", "opportunity.focus_areas", "organization.focus_areas"),
        ("population", "opportunity.beneficiaries", "organization.beneficiaries"),
        ("geography", "opportunity.geography", "organization.service_geographies"),
    )
    comparable = 0
    matched = 0
    matched_names = []
    for name, opportunity_key, organization_key in checks:
        opportunity_fact = context.fact(opportunity_key)
        organization_fact = context.fact(organization_key)
        if not (opportunity_fact and organization_fact):
            continue
        comparable += 1
        left = {token for token in opportunity_fact.value.casefold().replace(",", " ").split() if len(token) > 3}
        right = {token for token in organization_fact.value.casefold().replace(",", " ").split() if len(token) > 3}
        if left & right:
            matched += 1
            matched_names.append(name)

    if not comparable:
        return Metric(
            "Funder Alignment", INCOMPLETE, None,
            "The opportunity record does not yet list focus areas, population, or geography to compare against.",
        )
    basis = (
        f"{matched} of {comparable} comparable dimensions overlap"
        + (f" ({', '.join(matched_names)})" if matched_names else "")
        + "."
    )
    return Metric("Funder Alignment", _label_for(matched / comparable), None, basis)


def _evidence_metric(context: GrantContext) -> Metric:
    """Evidence strength, counted over the four evidence types funders ask for."""
    checks = {
        "outcome metrics": "evidence.outcome_metrics",
        "people served": "evidence.people_served",
        "community need data": "evidence.community_need",
        "past performance": "evidence.past_performance",
    }
    present = [name for name, key in checks.items() if context.fact(key)]
    ratio = len(present) / len(checks)
    basis = (
        f"{len(present)} of {len(checks)} evidence types available"
        + (f": {', '.join(present)}." if present else ". Nothing in the Evidence Library yet.")
    )
    return Metric("Evidence Strength", _label_for(ratio), None, basis)


def _budget_metric(context: GrantContext, application) -> Metric:
    checks = {
        "annual budget range": bool(context.fact("organization.budget_range")),
        "budget document": bool(context.fact("documents.budget")),
        "requested amount": application.requested_amount is not None,
    }
    present = [name for name, ok in checks.items() if ok]
    basis = (
        f"{len(present)} of {len(checks)} budget inputs present"
        + (f": {', '.join(present)}." if present else ".")
    )
    return Metric("Budget Alignment", _label_for(len(present) / len(checks)), None, basis)


def build_application_review(application, context: GrantContext, sections=None) -> ApplicationReview:
    """Everything the Review screen shows, computed from real section state.

    Once the real application has been imported, the funder's own questions are
    the yardstick — not Atlas's 14-section template. ``answerable_sections``
    makes that switch, so "7 of 10" always refers to what the funder asked.
    """
    all_sections = list(application.sections.all()) if sections is None else list(sections)
    sections = application.answerable_sections(all_sections)
    imported_mode = any(s.is_imported or s.source_type == GrantApplicationSection.SourceType.MANUAL
                        for s in sections)
    required = [section for section in sections if section.required]
    approved = [section for section in sections if section.is_approved]
    approved_required = [section for section in required if section.is_approved]

    # How many sections Atlas has enough information to write well right now.
    draftable = 0
    blocked = 0
    issues: list[Issue] = []
    needs_org_info = 0

    for section in sections:
        spec = spec_for(section.section_key) if not section.is_imported else None
        if spec is not None:
            missing = context.missing_for(spec.requirements)
        else:
            # Imported question: ask the analyzer what this question depends on.
            from openoutreach.grants.services.question_analysis import analyze_question
            missing = analyze_question(section, context).missing_information
        if missing:
            blocked += 1
            needs_org_info += 1
        else:
            draftable += 1

        if not section.current_text.strip():
            if section.required:
                issues.append(Issue(section.title, "No response drafted yet.", section.section_key))
            continue

        if spec is not None:
            review = grant_coach.review_section(section, context, spec)
            for finding in review.findings:
                if finding.kind in {grant_coach.UNSUPPORTED_CLAIM, grant_coach.POSSIBLE_MISMATCH}:
                    issues.append(Issue(section.title, finding.message, section.section_key))
            markers = review.information_needed_markers
        else:
            imported_review = grant_coach.review_imported_question(section, context)
            if imported_review.unsupported_numbers:
                issues.append(Issue(
                    section.title,
                    "Contains figures Atlas cannot trace to your organization data "
                    f"({', '.join(imported_review.unsupported_numbers[:4])}).",
                    section.section_key,
                ))
            markers = imported_review.information_needed_markers
        if markers:
            issues.append(Issue(
                section.title,
                f"{len(markers)} placeholder{'s' if len(markers) != 1 else ''} still to fill: "
                + "; ".join(markers[:3]),
                section.section_key,
            ))
        if section.over_character_limit:
            issues.append(Issue(
                section.title,
                f"Response exceeds the funder's {section.character_limit:,}-character limit.",
                section.section_key,
            ))
        elif section.over_word_limit:
            issues.append(Issue(
                section.title,
                f"Response exceeds the funder's {section.word_limit:,}-word limit.",
                section.section_key,
            ))
        if section.required and section.status != GrantApplicationSection.Status.APPROVED:
            issues.append(Issue(
                section.title, "Drafted but not yet approved by a person.", section.section_key,
            ))

    if application.deadline is None:
        issues.append(Issue("Application", "No deadline recorded for this opportunity."))

    # Attachment checklist — the funder asked for documents, not just answers.
    attachments = list(application.attachment_requirements.select_related("linked_document"))
    unconfirmed = [item for item in attachments if not item.is_satisfied]
    for item in unconfirmed:
        issues.append(Issue("Required attachments", f"{item.title} is not confirmed yet."))

    completion = application.completion_percent(sections)
    required_count = len(required) or len(sections)
    unit = "questions" if imported_mode else "sections"

    metrics = [
        Metric(
            "Application Completeness",
            f"{completion}%",
            completion,
            f"{len(approved_required)} of {required_count} required {unit} approved; "
            "drafted-but-unapproved answers count half.",
        ),
        Metric(
            "Required Questions Complete" if imported_mode else "Required Sections Complete",
            f"{len(approved_required)} / {required_count}",
            None,
            (
                f"{needs_org_info} {'question' if needs_org_info == 1 else 'questions'} still need "
                f"organization information. "
                + (
                    f"{len(unconfirmed)} of {len(attachments)} required attachments not confirmed."
                    if attachments else "No attachment requirements recorded."
                )
            ),
        ),
        Metric(
            "Information Coverage",
            f"{context.requirement_coverage}%",
            context.requirement_coverage,
            f"{sum(1 for ok in context.resolved_requirements.values() if ok)} of "
            f"{len(context.resolved_requirements)} information requirements are satisfied by "
            "your Atlas profile, Evidence Library, and Document Vault.",
        ),
        _alignment_metric(context),
        _evidence_metric(context),
        _budget_metric(context, application),
    ]

    return ApplicationReview(
        completion_percent=completion,
        metrics=metrics,
        issues=issues,
        approved_sections=len(approved),
        required_sections=required_count,
        draftable_sections=draftable,
        blocked_sections=blocked,
    )
