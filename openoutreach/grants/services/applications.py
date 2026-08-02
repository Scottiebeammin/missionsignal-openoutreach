"""Creating and maintaining a grant workspace.

Also the bridge to the existing Atlas Readiness system: Grant Builder does not
compute a second, unrelated readiness score. It reuses
``signals.readiness.build_organization_completeness`` for the organization-level
number and adds the one question readiness could not answer before — *how ready
are we to actually complete THIS application?*
"""
from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone

from openoutreach.grants.models import GrantApplication, GrantApplicationSection
from openoutreach.grants.services.context_builder import GrantContext, MissingFact
from openoutreach.grants.services.template import sections_for, spec_for


def start_grant_application(project, opportunity, user=None) -> tuple[GrantApplication, bool]:
    """Open (or re-open) the workspace for this project + opportunity.

    Returns ``(application, created)``. Idempotent: a second "Start Grant Draft"
    click lands the user back in the existing draft rather than duplicating it.
    """
    application, created = GrantApplication.objects.get_or_create(
        project=project,
        opportunity=opportunity,
        defaults={
            "title": opportunity.name,
            "funder_name": (
                str(opportunity.source_organization) if opportunity.source_organization
                else opportunity.source_name
            ),
            "deadline": opportunity.deadline,
            "requested_amount": opportunity.funding_amount,
            "source_url": opportunity.real_source_url() or "",
            "status": GrantApplication.Status.DRAFTING,
            "created_by": user,
        },
    )
    sync_sections(application)
    return application, created


def sync_sections(application) -> list[GrantApplicationSection]:
    """Ensure the application has a row per template section.

    Read-mostly: only writes when a section is genuinely absent, so opening the
    workspace on an existing draft costs one query. Existing rows are never
    rewritten — a user's question text, limits, and answers survive template
    changes.
    """
    existing = {section.section_key: section for section in application.sections.all()}
    created = False
    for spec in sections_for(application.opportunity):
        if spec.key in existing:
            continue
        GrantApplicationSection.objects.create(
            application=application,
            section_key=spec.key,
            title=spec.title,
            order=spec.order,
            required=spec.required,
            funder_question=spec.question,
            guidance=list(spec.guidance),
            word_limit=spec.word_limit,
            character_limit=spec.character_limit,
        )
        created = True
    if created:
        return list(application.sections.all())
    return sorted(existing.values(), key=lambda section: (section.order, section.pk))


def approve_section(section, text, user=None) -> GrantApplicationSection:
    """Record a human-approved answer.

    The approved column is the only place approved text lives, and only this
    function writes it. AI never calls it.
    """
    section.approved_response = text
    section.status = GrantApplicationSection.Status.APPROVED
    section.approved_at = timezone.now()
    section.approved_by = user
    section.save(update_fields=[
        "approved_response", "status", "approved_at", "approved_by", "updated_at",
    ])
    return section


def unapprove_section(section) -> GrantApplicationSection:
    """Send an approved answer back to draft, keeping the text as the draft."""
    section.draft_response = section.approved_response or section.draft_response
    section.approved_response = ""
    section.approved_at = None
    section.approved_by = None
    section.status = (
        GrantApplicationSection.Status.DRAFTED if section.draft_response
        else GrantApplicationSection.Status.NOT_STARTED
    )
    section.save(update_fields=[
        "draft_response", "approved_response", "approved_at", "approved_by", "status", "updated_at",
    ])
    return section


@dataclass(frozen=True)
class GrantReadiness:
    """How ready this organization is to actually finish this application."""

    score: int
    level: str
    organization_score: int
    draftable_sections: int
    total_sections: int
    still_needed: list[MissingFact]

    @property
    def draftable_label(self) -> str:
        return f"{self.draftable_sections} of {self.total_sections} sections"


def _level(score: int) -> str:
    if score >= 85:
        return "Advanced"
    if score >= 70:
        return "Competitive"
    if score >= 50:
        return "Developing"
    return "Emerging"


def build_grant_readiness(application, context: GrantContext, sections=None) -> GrantReadiness:
    """Grant-preparation readiness, built on the existing Readiness system.

    The organization half comes from ``build_organization_completeness`` — the
    same score the Readiness dashboard shows. The application half is the share
    of sections Atlas holds enough information to draft well. Averaging the two
    answers the question a client actually asks here: can we finish this?
    """
    from openoutreach.signals.readiness import build_organization_completeness

    sections = list(application.sections.all()) if sections is None else list(sections)
    organization_completeness = build_organization_completeness(application.project)

    draftable = 0
    for section in sections:
        spec = spec_for(section.section_key)
        if spec is None:
            continue
        if not context.missing_for(spec.requirements):
            draftable += 1

    section_score = round((draftable / len(sections)) * 100) if sections else 0
    score = round((organization_completeness.score + section_score) / 2)
    return GrantReadiness(
        score=score,
        level=_level(score),
        organization_score=organization_completeness.score,
        draftable_sections=draftable,
        total_sections=len(sections),
        still_needed=context.all_missing,
    )
