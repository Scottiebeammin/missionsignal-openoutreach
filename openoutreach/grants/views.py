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

from openoutreach.funding.models import DocumentVaultItem, Opportunity
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
        # V1.1: what the funder said outside any single question, and the
        # documents they asked to be attached.
        "application_instructions": _application_instructions(application),
        "attachment_requirements": list(
            application.attachment_requirements.select_related("linked_document")
        ),
        "has_imported_questions": application.has_imported_questions,
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
    from openoutreach.grants.services.question_analysis import analyze_question

    rows = []
    for section in sections:
        spec = spec_for(section.section_key) if not section.is_imported else None
        if spec is not None:
            missing = context.missing_for(spec.requirements)
            available = context.available_labels(spec.fact_keys)
            ready = True
        else:
            analysis = analyze_question(section, context)
            missing = analysis.missing_information
            available = analysis.known_labels
            ready = analysis.can_generate_draft
        rows.append({
            "section": section,
            "missing": missing,
            "available": available,
            "ready": ready,
            "group": section.section_group,
        })
    return render(request, "grants/grant_application.html", {
        "project": project,
        "organization": project.organization,
        "application": application,
        "rows": rows,
        "completion": application.completion_percent(sections),
        "has_imported_questions": application.has_imported_questions,
        "active_page": "grants",
        **_nav(application, "application"),
    })


@login_required
def grant_section_view(request, pk, application_id, section_key):
    """The answer workspace for one section."""
    project, application = _application(request, pk, application_id)
    section = _section(application, section_key)
    spec = spec_for(section.section_key) if not section.is_imported else None
    context = build_grant_context(application)

    # Imported questions get the three-bucket analysis and the five-dimension
    # coach; template sections keep the V1 behaviour unchanged.
    from openoutreach.grants.services.question_analysis import analyze_question

    if section.is_imported or spec is None:
        analysis = analyze_question(section, context)
        review = None
        imported_review = grant_coach.review_imported_question(section, context, analysis)
        available_facts = analysis.known_facts
        missing = analysis.missing_information
        library_matches = analysis.relevant_answer_library_items
        suggestions = []
    else:
        analysis = None
        review = grant_coach.review_section(section, context, spec)
        imported_review = None
        available_facts = context.facts_for(spec.fact_keys)
        missing = context.missing_for(spec.requirements)
        library_matches = []
        suggestions = answer_library.suggestions_for_section(section, spec)

    sections = list(application.sections.all())
    index = next((i for i, item in enumerate(sections) if item.pk == section.pk), 0)

    return render(request, "grants/grant_section.html", {
        "project": project,
        "organization": project.organization,
        "application": application,
        "section": section,
        "spec": spec,
        "analysis": analysis,
        "imported_review": imported_review,
        "library_matches": library_matches,
        "available_facts": available_facts,
        "missing": missing,
        "suggestions": suggestions,
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
    spec = spec_for(section.section_key) if not section.is_imported else None
    context = build_grant_context(application)

    from openoutreach.grants.services.question_analysis import analyze_question

    analysis = None
    if spec is None:
        analysis = analyze_question(section, context)
        if not analysis.can_generate_draft:
            messages.error(request, analysis.gate_reason)
            return redirect(
                "project-grant-section", pk=pk, application_id=application_id, section_key=section_key,
            )
        reusable = [match.item for match in analysis.relevant_answer_library_items]
    else:
        reusable = answer_library.suggestions_for_section(section, spec)

    action = (request.POST.get("action") or "").strip()

    try:
        if action:
            source_text = section.draft_response or section.approved_response
            if not source_text.strip():
                messages.error(request, "Write or generate a response before refining it.")
                return redirect(
                    "project-grant-section", pk=pk, application_id=application_id, section_key=section_key,
                )
            draft = draft_generator.refine_section_draft(
                section, context, spec, action, source_text, analysis=analysis,
            )
        else:
            draft = draft_generator.generate_section_draft(
                section, context, spec, reusable=reusable, analysis=analysis,
            )
    except GrantBuilderError as exc:
        messages.error(request, str(exc))
        return redirect(
            "project-grant-section", pk=pk, application_id=application_id, section_key=section_key,
        )

    missing = (
        context.missing_for(spec.requirements) if spec is not None
        else analysis.missing_information
    )
    # Prefer Atlas's own view of what is missing (checked against real records)
    # over the model's self-report, then fold in anything extra the model named.
    missing_labels = [item.label for item in missing]
    for label in draft.missing_information:
        if label and label not in missing_labels:
            missing_labels.append(label)

    candidate_facts = (
        context.facts_for(spec.fact_keys) if spec is not None else analysis.known_facts
    )
    section.draft_response = draft.response
    section.source_fields = [
        {"key": fact.key, "label": fact.label} for fact in candidate_facts
        if not draft.sources_used or fact.label in draft.sources_used
    ] or [{"key": fact.key, "label": fact.label} for fact in candidate_facts]
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


# ── V1.1: real application import ────────────────────────────────────────────

@login_required
def grant_import(request, pk, application_id):
    """Paste a real application. Parsing only — no answers are generated here."""
    project, application = _application(request, pk, application_id)

    if request.method == "POST":
        raw_text = request.POST.get("raw_text") or ""
        if not raw_text.strip():
            messages.error(request, "Paste the application text before analyzing it.")
        else:
            from openoutreach.grants.services import imports
            from openoutreach.grants.services.application_parser import parse_application

            _apply_detail_edits(request, application)
            parsed = parse_application(raw_text)
            batch = imports.create_import(
                application, raw_text, parsed, user=request.user,
                source_label=(request.POST.get("source_label") or "").strip(),
            )
            request.session[f"grant_import_{batch.pk}"] = {
                "questions": [
                    {
                        "text": q.text, "label": q.label, "section_group": q.section_group,
                        "instructions": q.instructions, "question_type": q.question_type,
                        "required": q.required, "word_limit": q.word_limit,
                        "character_limit": q.character_limit, "page_limit_note": q.page_limit_note,
                        "scoring_notes": q.scoring_notes, "order": q.order,
                    }
                    for q in parsed.questions
                ],
                "attachments": [
                    {"title": a.title, "document_type": a.document_type} for a in parsed.attachments
                ],
                "unparsed": parsed.unparsed_blocks,
            }
            return redirect(
                "project-grant-import-review", pk=pk, application_id=application_id, batch_id=batch.pk,
            )

    return render(request, "grants/grant_import.html", {
        "project": project,
        "organization": project.organization,
        "application": application,
        "statuses": GrantApplication.Status.choices,
        "active_page": "grants",
        **_nav(application, "application"),
    })


def _apply_detail_edits(request, application):
    """Let the import screen correct the header facts while it is open."""
    from decimal import Decimal, InvalidOperation

    changed = []
    title = (request.POST.get("title") or "").strip()
    funder = (request.POST.get("funder_name") or "").strip()
    deadline = (request.POST.get("deadline") or "").strip()
    amount = (request.POST.get("requested_amount") or "").replace(",", "").replace("$", "").strip()

    if title and title != application.title:
        application.title = title[:500]
        changed.append("title")
    if funder and funder != application.funder_name:
        application.funder_name = funder[:500]
        changed.append("funder_name")
    if deadline:
        parsed_date = parse_date(deadline)
        if parsed_date and parsed_date != application.deadline:
            application.deadline = parsed_date
            changed.append("deadline")
    if amount:
        try:
            value = Decimal(amount)
        except InvalidOperation:
            value = None
        if value is not None and value != application.requested_amount:
            application.requested_amount = value
            changed.append("requested_amount")
    if changed:
        application.save(update_fields=[*changed, "updated_at"])


@login_required
def grant_import_review(request, pk, application_id, batch_id):
    """Review and correct what the parser found, then save. Human review is required."""
    from openoutreach.grants.models import GrantApplicationImport
    from openoutreach.grants.services import imports

    project, application = _application(request, pk, application_id)
    batch = get_object_or_404(GrantApplicationImport, pk=batch_id, application=application)
    cached = request.session.get(f"grant_import_{batch.pk}") or {}

    if request.method == "POST":
        questions = imports.questions_from_post(request.POST)
        attachments = imports.attachments_from_post(request.POST)
        if not questions:
            messages.error(request, "Add at least one question before saving.")
        else:
            instructions = [
                line.strip()
                for line in (request.POST.get("application_instructions") or "").splitlines()
                if line.strip()
            ]
            batch.application_instructions = instructions
            batch.save(update_fields=["application_instructions"])
            created = imports.save_imported_questions(batch, questions, attachments)
            request.session.pop(f"grant_import_{batch.pk}", None)
            messages.success(
                request,
                f"Saved {len(created)} question{'s' if len(created) != 1 else ''} from the application.",
            )
            return redirect("project-grant-application", pk=pk, application_id=application_id)

    return render(request, "grants/grant_import_review.html", {
        "project": project,
        "organization": project.organization,
        "application": application,
        "batch": batch,
        "questions": cached.get("questions", []),
        "attachments": cached.get("attachments", []),
        "unparsed": cached.get("unparsed", []),
        "instructions_text": "\n".join(batch.application_instructions or []),
        "question_types": GrantApplicationSection.QuestionType.choices,
        "document_types": DocumentVaultItem.DocumentType.choices,
        "active_page": "grants",
        **_nav(application, "application"),
    })


@login_required
@require_POST
def grant_attachment_toggle(request, pk, application_id, requirement_id):
    """Tick or untick one attachment on the checklist."""
    from openoutreach.grants.models import GrantAttachmentRequirement

    _project, application = _application(request, pk, application_id)
    requirement = get_object_or_404(
        GrantAttachmentRequirement, pk=requirement_id, application=application,
    )
    requirement.confirmed = not requirement.confirmed
    requirement.save(update_fields=["confirmed", "updated_at"])
    return redirect(request.POST.get("next") or reverse(
        "project-grant-overview", args=[pk, application_id],
    ))


def _application_instructions(application) -> list[str]:
    """Application-wide rules from every import, newest first, de-duplicated.

    These belong to the application, not to any one question, so parsing must
    never lose them — they are shown on the overview.
    """
    seen: set[str] = set()
    lines: list[str] = []
    for batch in application.imports.all():
        for line in batch.application_instructions or []:
            key = line.strip().casefold()
            if key and key not in seen:
                seen.add(key)
                lines.append(line.strip())
    return lines
