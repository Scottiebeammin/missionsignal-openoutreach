"""Atlas Grant Builder — portal views.

Permissions reuse ``signals.views.client_project``: a project is reachable only
by its own members (staff can view-as-client). Every object below is fetched
*through* that project, so there is no path to another organization's draft,
section, or Answer Library item.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.utils.dateparse import parse_date
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from openoutreach.funding.models import Opportunity
from openoutreach.grants.exceptions import GrantBuilderError
from openoutreach.grants.models import (
    GrantAnswerLibraryItem,
    GrantApplication,
    GrantApplicationSection,
)
from openoutreach.grants.services import answer_library, completeness, draft_generator, grant_coach
from openoutreach.grants.services.applications import (
    approve_section,
    build_grant_readiness,
    start_grant_application,
    sync_sections,
    unapprove_section,
)
from openoutreach.grants.services.context_builder import build_grant_context
from openoutreach.grants.services.draft_generator import ACTION_LABELS
from openoutreach.grants.services.template import spec_for
from openoutreach.signals.views import client_project


def _application(request, pk, application_id) -> tuple[object, GrantApplication]:
    """The project the user may see, and a draft that belongs to it."""
    project = client_project(request, pk)
    application = get_object_or_404(
        GrantApplication.objects.select_related("opportunity", "project__organization"),
        pk=application_id,
        project=project,
    )
    return project, application


def _section(application, section_key) -> GrantApplicationSection:
    return get_object_or_404(
        GrantApplicationSection, application=application, section_key=section_key,
    )


def _nav(application, active):
    return {
        "grant_nav_active": active,
        "grant_nav": [
            ("overview", "Overview", reverse("project-grant-overview", args=[application.project_id, application.pk])),
            ("application", "Application", reverse("project-grant-application", args=[application.project_id, application.pk])),
            ("missing", "Missing Information", reverse("project-grant-missing", args=[application.project_id, application.pk])),
            ("library", "Answer Library", reverse("project-grant-library", args=[application.project_id, application.pk])),
            ("review", "Review", reverse("project-grant-review", args=[application.project_id, application.pk])),
        ],
    }


# ── Index + start ────────────────────────────────────────────────────────────

@login_required
def grant_list(request, pk):
    """Every grant draft on this project, with the empty state for a new org."""
    project = client_project(request, pk)
    applications = list(
        GrantApplication.objects.filter(project=project)
        .select_related("opportunity")
        .prefetch_related("sections")
    )
    rows = [
        {"application": application, "completion": application.completion_percent()}
        for application in applications
    ]
    return render(request, "grants/grant_list.html", {
        "project": project,
        "organization": project.organization,
        "rows": rows,
        "library_count": answer_library.library_for(project.organization).count(),
        "active_page": "grants",
    })


@login_required
@require_POST
def grant_start(request, pk, opportunity_id):
    """Start Grant Draft — or continue the existing one for this opportunity."""
    project = client_project(request, pk)
    opportunity = get_object_or_404(
        Opportunity.objects.select_related("source_organization"),
        pk=opportunity_id,
        project=project,
    )
    application, created = start_grant_application(project, opportunity, user=request.user)
    if created:
        messages.success(request, f"Grant draft started for {application.title}.")
    return redirect("project-grant-overview", pk=pk, application_id=application.pk)


# ── Workspace ────────────────────────────────────────────────────────────────

@login_required
def grant_overview(request, pk, application_id):
    project, application = _application(request, pk, application_id)
    sections = sync_sections(application)
    context = build_grant_context(application)
    readiness = build_grant_readiness(application, context, sections)
    review = completeness.build_application_review(application, context, sections)

    return render(request, "grants/grant_overview.html", {
        "project": project,
        "organization": project.organization,
        "application": application,
        "opportunity": application.opportunity,
        "sections": sections,
        "completion": application.completion_percent(sections),
        "readiness": readiness,
        "review": review,
        "known_facts": sorted(
            (fact for fact in context.facts.values()), key=lambda fact: fact.label,
        ),
        "statuses": GrantApplication.Status.choices,
        "active_page": "grants",
        **_nav(application, "overview"),
    })


@login_required
def grant_application_view(request, pk, application_id):
    """All sections at a glance, with per-section state and counts."""
    project, application = _application(request, pk, application_id)
    sections = sync_sections(application)
    context = build_grant_context(application)
    rows = []
    for section in sections:
        spec = spec_for(section.section_key)
        rows.append({
            "section": section,
            "missing": context.missing_for(spec.requirements) if spec else [],
            "available": context.available_labels(spec.fact_keys) if spec else [],
        })
    return render(request, "grants/grant_application.html", {
        "project": project,
        "organization": project.organization,
        "application": application,
        "rows": rows,
        "completion": application.completion_percent(sections),
        "active_page": "grants",
        **_nav(application, "application"),
    })


@login_required
def grant_section_view(request, pk, application_id, section_key):
    """The answer workspace for one section."""
    project, application = _application(request, pk, application_id)
    section = _section(application, section_key)
    spec = spec_for(section.section_key)
    context = build_grant_context(application)

    review = grant_coach.review_section(section, context, spec) if spec else None
    sections = list(application.sections.all())
    index = next((i for i, item in enumerate(sections) if item.pk == section.pk), 0)

    return render(request, "grants/grant_section.html", {
        "project": project,
        "organization": project.organization,
        "application": application,
        "section": section,
        "spec": spec,
        "available_facts": context.facts_for(spec.fact_keys) if spec else [],
        "missing": context.missing_for(spec.requirements) if spec else [],
        "suggestions": answer_library.suggestions_for_section(section, spec) if spec else [],
        "review": review,
        "actions": ACTION_LABELS,
        "previous_section": sections[index - 1] if index > 0 else None,
        "next_section": sections[index + 1] if index + 1 < len(sections) else None,
        "active_page": "grants",
        **_nav(application, "application"),
    })


@login_required
@require_POST
def grant_section_generate(request, pk, application_id, section_key):
    """Generate or refine the DRAFT for a section. Never touches approved text."""
    _project, application = _application(request, pk, application_id)
    section = _section(application, section_key)
    spec = spec_for(section.section_key)
    if spec is None:
        messages.error(request, "This section is no longer part of the grant template.")
        return redirect("project-grant-section", pk=pk, application_id=application_id, section_key=section_key)

    context = build_grant_context(application)
    action = (request.POST.get("action") or "").strip()

    try:
        if action:
            source_text = section.draft_response or section.approved_response
            if not source_text.strip():
                messages.error(request, "Write or generate a response before refining it.")
                return redirect(
                    "project-grant-section", pk=pk, application_id=application_id, section_key=section_key,
                )
            draft = draft_generator.refine_section_draft(section, context, spec, action, source_text)
        else:
            draft = draft_generator.generate_section_draft(
                section, context, spec,
                reusable=answer_library.suggestions_for_section(section, spec),
            )
    except GrantBuilderError as exc:
        messages.error(request, str(exc))
        return redirect(
            "project-grant-section", pk=pk, application_id=application_id, section_key=section_key,
        )

    missing = context.missing_for(spec.requirements)
    # Prefer Atlas's own view of what is missing (checked against real records)
    # over the model's self-report, then fold in anything extra the model named.
    missing_labels = [item.label for item in missing]
    for label in draft.missing_information:
        if label and label not in missing_labels:
            missing_labels.append(label)

    section.draft_response = draft.response
    section.source_fields = [
        {"key": fact.key, "label": fact.label} for fact in context.facts_for(spec.fact_keys)
        if not draft.sources_used or fact.label in draft.sources_used
    ] or [{"key": fact.key, "label": fact.label} for fact in context.facts_for(spec.fact_keys)]
    section.missing_information = missing_labels
    # An approved section STAYS approved. Generating produces an alternative
    # draft alongside the approved answer; only a person can promote it.
    if not section.is_approved:
        section.status = (
            GrantApplicationSection.Status.NEEDS_INFORMATION if missing_labels
            else GrantApplicationSection.Status.DRAFTED
        )
    section.last_generated_at = timezone.now()
    section.save(update_fields=[
        "draft_response", "source_fields", "missing_information", "status",
        "last_generated_at", "updated_at",
    ])

    if application.status == GrantApplication.Status.NOT_STARTED:
        application.status = GrantApplication.Status.DRAFTING
        application.save(update_fields=["status", "updated_at"])

    messages.success(
        request,
        f"{ACTION_LABELS.get(action, 'Draft')} applied to {section.title}."
        if action else f"Draft generated for {section.title}.",
    )
    return redirect("project-grant-section", pk=pk, application_id=application_id, section_key=section_key)


@login_required
@require_POST
def grant_section_save(request, pk, application_id, section_key):
    """Save edits, approve, or send an approved answer back to draft."""
    _project, application = _application(request, pk, application_id)
    section = _section(application, section_key)
    intent = request.POST.get("intent", "save")

    if intent == "unapprove":
        unapprove_section(section)
        messages.success(request, f"{section.title} moved back to draft.")
        return redirect("project-grant-section", pk=pk, application_id=application_id, section_key=section_key)

    text = (request.POST.get("response") or "").strip()
    word_limit = (request.POST.get("word_limit") or "").strip()
    character_limit = (request.POST.get("character_limit") or "").strip()
    section.word_limit = int(word_limit) if word_limit.isdigit() and int(word_limit) else None
    section.character_limit = (
        int(character_limit) if character_limit.isdigit() and int(character_limit) else None
    )
    question = (request.POST.get("funder_question") or "").strip()
    if question:
        section.funder_question = question

    if intent == "approve":
        section.draft_response = ""
        section.save(update_fields=[
            "draft_response", "word_limit", "character_limit", "funder_question", "updated_at",
        ])
        approve_section(section, text, user=request.user)
        messages.success(request, f"{section.title} approved.")
    else:
        # Editing an approved answer keeps it approved — a person wrote it.
        if section.is_approved:
            section.approved_response = text
        else:
            section.draft_response = text
            if text and section.status == GrantApplicationSection.Status.NOT_STARTED:
                section.status = GrantApplicationSection.Status.DRAFTED
        section.save(update_fields=[
            "draft_response", "approved_response", "status", "word_limit",
            "character_limit", "funder_question", "updated_at",
        ])
        messages.success(request, f"{section.title} saved.")

    return redirect("project-grant-section", pk=pk, application_id=application_id, section_key=section_key)


@login_required
def grant_missing(request, pk, application_id):
    """Everything Atlas needs before it can finish this application."""
    project, application = _application(request, pk, application_id)
    sections = sync_sections(application)
    context = build_grant_context(application)
    readiness = build_grant_readiness(application, context, sections)

    rows = []
    for item in context.all_missing:
        blocked = []
        for section in sections:
            spec = spec_for(section.section_key)
            if spec and item.key in spec.requirements:
                blocked.append(section)
        rows.append({"item": item, "sections": blocked})

    return render(request, "grants/grant_missing.html", {
        "project": project,
        "organization": project.organization,
        "application": application,
        "rows": rows,
        "readiness": readiness,
        "active_page": "grants",
        **_nav(application, "missing"),
    })


# ── Answer Library ───────────────────────────────────────────────────────────

@login_required
def grant_library(request, pk, application_id):
    project, application = _application(request, pk, application_id)
    category = request.GET.get("category") or None
    items = list(answer_library.library_for(project.organization, category=category))
    return render(request, "grants/grant_library.html", {
        "project": project,
        "organization": project.organization,
        "application": application,
        "items": items,
        "categories": answer_library.category_counts(project.organization),
        "selected_category": category,
        "sections": list(application.sections.all()),
        "active_page": "grants",
        **_nav(application, "library"),
    })


@login_required
@require_POST
def grant_library_save(request, pk, application_id, section_key):
    """Promote an approved answer to the organization's Answer Library."""
    _project, application = _application(request, pk, application_id)
    section = _section(application, section_key)
    try:
        item = answer_library.save_section_to_library(
            section, user=request.user, title=(request.POST.get("title") or "").strip(),
        )
    except ValueError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, f"Saved “{item.title}” to your Answer Library.")
    return redirect("project-grant-section", pk=pk, application_id=application_id, section_key=section_key)


@login_required
@require_POST
def grant_library_reuse(request, pk, application_id, item_id):
    """Reuse a library answer as a draft. The library item is never modified."""
    project, application = _application(request, pk, application_id)
    item = get_object_or_404(
        GrantAnswerLibraryItem, pk=item_id, organization=project.organization,
    )
    section = _section(application, request.POST.get("section_key", ""))
    if section.is_approved:
        messages.error(
            request,
            f"{section.title} is already approved. Move it back to draft first if you want to replace it.",
        )
        return redirect("project-grant-section", pk=pk, application_id=application_id, section_key=section.section_key)

    answer_library.reuse_into_section(item, section, replace=request.POST.get("mode") == "replace")
    messages.success(request, f"Added “{item.title}” to {section.title} as a draft to adapt.")
    return redirect("project-grant-section", pk=pk, application_id=application_id, section_key=section.section_key)


# ── Review, status, export ───────────────────────────────────────────────────

@login_required
def grant_review(request, pk, application_id):
    project, application = _application(request, pk, application_id)
    sections = sync_sections(application)
    context = build_grant_context(application)
    review = completeness.build_application_review(application, context, sections)
    readiness = build_grant_readiness(application, context, sections)
    return render(request, "grants/grant_review.html", {
        "project": project,
        "organization": project.organization,
        "application": application,
        "review": review,
        "readiness": readiness,
        "sections": sections,
        "statuses": GrantApplication.Status.choices,
        "active_page": "grants",
        **_nav(application, "review"),
    })


@login_required
@require_POST
def grant_status_update(request, pk, application_id):
    _project, application = _application(request, pk, application_id)
    target = request.POST.get("status", "")
    if target not in GrantApplication.Status.values:
        messages.error(request, "Unknown grant status.")
    else:
        application.status = target
        application.save(update_fields=["status", "updated_at"])
        messages.success(request, f"Status set to {application.get_status_display()}.")
    return redirect(request.POST.get("next") or reverse(
        "project-grant-overview", args=[pk, application_id],
    ))


@login_required
@require_POST
def grant_details_update(request, pk, application_id):
    """Edit the workspace header facts a person owns (never AI-written)."""
    _project, application = _application(request, pk, application_id)
    application.funder_name = (request.POST.get("funder_name") or "").strip()

    # These are typed columns, so parse before assigning — a stray character in a
    # free-text field must not 500 the workspace.
    raw_amount = (request.POST.get("requested_amount") or "").replace(",", "").replace("$", "").strip()
    try:
        application.requested_amount = Decimal(raw_amount) if raw_amount else None
    except InvalidOperation:
        messages.error(request, f"“{raw_amount}” is not a valid amount — the requested amount was left unchanged.")

    raw_deadline = (request.POST.get("deadline") or "").strip()
    application.deadline = parse_date(raw_deadline) if raw_deadline else None

    application.save(update_fields=["funder_name", "requested_amount", "deadline", "updated_at"])
    messages.success(request, "Grant details updated.")
    return redirect("project-grant-overview", pk=pk, application_id=application_id)


@login_required
def grant_export(request, pk, application_id):
    """The full application draft in one place, ready to copy into the real form."""
    project, application = _application(request, pk, application_id)
    sections = sync_sections(application)
    context = build_grant_context(application)
    review = completeness.build_application_review(application, context, sections)
    return render(request, "grants/grant_export.html", {
        "project": project,
        "organization": project.organization,
        "application": application,
        "sections": [section for section in sections if section.current_text.strip()],
        "empty_sections": [section for section in sections if not section.current_text.strip()],
        "review": review,
        "active_page": "grants",
        **_nav(application, "review"),
    })
