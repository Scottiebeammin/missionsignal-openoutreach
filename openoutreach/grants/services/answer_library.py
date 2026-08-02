"""The organization's reusable grant knowledge.

The point of the library is that an organization should never have to describe
itself from scratch twice. An approved answer is promoted here, and the next
application that reaches the same kind of question is offered it.

Two invariants:

- Every read is scoped to a single organization. There is no query in this
  module that can return another organization's answers.
- Reuse never overwrites the original. ``reuse_into_section`` copies text into
  the section's DRAFT column; the library item is untouched.
"""
from __future__ import annotations

from django.utils import timezone

from openoutreach.grants.models import GrantAnswerLibraryItem, GrantApplicationSection


def library_for(organization, *, category=None, approved_only=True):
    """Every library answer this organization owns, newest first within category."""
    items = GrantAnswerLibraryItem.objects.filter(organization=organization)
    if approved_only:
        items = items.filter(approval_status=GrantAnswerLibraryItem.ApprovalStatus.APPROVED)
    if category:
        items = items.filter(category=category)
    return items.select_related("source_application", "project")


def suggestions_for_section(section, spec, *, limit=3):
    """Approved answers worth adapting for this section.

    Matched on the section's library category, excluding anything this very
    section already produced (so a saved answer doesn't suggest itself back).
    """
    organization = section.application.project.organization
    items = library_for(organization, category=spec.library_category)
    return list(items.exclude(source_section=section)[:limit])


def save_section_to_library(section, *, user=None, title="", category=None, tags=None):
    """Promote a section's approved answer to organization-level knowledge.

    Only approved text is eligible — an unreviewed AI draft must never become
    the organization's reusable description of itself.
    """
    from openoutreach.grants.services.template import spec_for

    if section.status != GrantApplicationSection.Status.APPROVED:
        raise ValueError("Only an approved answer can be saved to the Answer Library.")

    spec = spec_for(section.section_key)
    application = section.application
    return GrantAnswerLibraryItem.objects.create(
        organization=application.project.organization,
        project=application.project,
        category=category or (spec.library_category if spec else GrantAnswerLibraryItem.Category.OTHER),
        title=(title or "").strip() or f"{section.title} — {application.title}",
        answer=section.approved_response,
        approval_status=GrantAnswerLibraryItem.ApprovalStatus.APPROVED,
        source_application=application,
        source_section=section,
        source_grant_title=application.title,
        source_fields=list(section.source_fields or []),
        tags=list(tags or []),
        created_by=user,
        updated_by=user,
    )


def reuse_into_section(item, section, *, replace=False):
    """Copy a library answer into a section's draft.

    ``replace=False`` (the default) appends beneath whatever draft is already
    there, so nothing the user wrote is lost. The approved column is never
    touched by this call, and neither is the library item.
    """
    existing = section.draft_response.strip()
    if replace or not existing:
        section.draft_response = item.answer
    else:
        section.draft_response = f"{existing}\n\n{item.answer}"

    label = f"Answer Library: {item.title}"
    sources = list(section.source_fields or [])
    if not any(entry.get("label") == label for entry in sources):
        sources.append({"key": f"library.{item.pk}", "label": label})
    section.source_fields = sources

    if section.status == GrantApplicationSection.Status.NOT_STARTED:
        section.status = GrantApplicationSection.Status.DRAFTED
    section.last_generated_at = timezone.now()
    section.save(update_fields=[
        "draft_response", "source_fields", "status", "last_generated_at", "updated_at",
    ])
    return section


def category_counts(organization) -> list[tuple[str, str, int]]:
    """(value, label, count) per category, for the library index."""
    counts = {}
    for item in library_for(organization):
        counts[item.category] = counts.get(item.category, 0) + 1
    return [
        (value, label, counts[value])
        for value, label in GrantAnswerLibraryItem.Category.choices
        if value in counts
    ]
