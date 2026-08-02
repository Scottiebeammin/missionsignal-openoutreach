"""Persisting a reviewed application import.

The parser proposes; a person disposes. Nothing here runs during parsing — these
functions only execute after the import-review screen has been through a human,
which is why the review form's values (not the parser's) are what get saved.
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from openoutreach.funding.models import DocumentVaultItem
from openoutreach.grants.models import (
    GrantApplicationImport,
    GrantApplicationSection,
    GrantAttachmentRequirement,
)

# Imported questions get their own key namespace so they can never collide with
# a standard-template key like "organization_overview".
IMPORTED_KEY_PREFIX = "q"


def create_import(application, raw_text, parsed, user=None, source_label="") -> GrantApplicationImport:
    """Record the paste and what the parser made of it, pending review."""
    return GrantApplicationImport.objects.create(
        application=application,
        raw_text=raw_text,
        source_label=source_label,
        application_instructions=list(parsed.application_instructions),
        parse_confidence=parsed.confidence,
        parse_notes=list(parsed.notes),
        detected_question_count=parsed.question_count,
        created_by=user,
    )


def _next_key(existing_keys: set[str], index: int) -> str:
    key = f"{IMPORTED_KEY_PREFIX}{index}"
    bump = index
    while key in existing_keys:
        bump += 1
        key = f"{IMPORTED_KEY_PREFIX}{bump}"
    existing_keys.add(key)
    return key


@transaction.atomic
def save_imported_questions(batch, questions, attachments=(), replace_previous=True) -> list[GrantApplicationSection]:
    """Write the reviewed questions onto the application.

    ``questions`` is a list of dicts from the review form — already corrected by
    a person. ``replace_previous`` clears earlier imported rows so re-importing
    a corrected paste does not leave stale duplicates; **template sections and
    anything already approved are never touched.**
    """
    application = batch.application

    if replace_previous:
        stale = application.sections.filter(
            source_type__in=(
                GrantApplicationSection.SourceType.IMPORTED,
                GrantApplicationSection.SourceType.MANUAL,
            ),
        ).exclude(status=GrantApplicationSection.Status.APPROVED)
        stale.delete()

    existing_keys = set(application.sections.values_list("section_key", flat=True))
    created: list[GrantApplicationSection] = []

    for index, entry in enumerate(questions, start=1):
        text = (entry.get("text") or "").strip()
        if not text:
            continue
        section = GrantApplicationSection.objects.create(
            application=application,
            section_key=_next_key(existing_keys, index),
            title=_title_for(entry, index),
            order=index,
            imported_order=index,
            imported_label=(entry.get("label") or "").strip()[:40],
            required=bool(entry.get("required", True)),
            # Both columns start identical; `original_question` is then frozen.
            funder_question=text,
            original_question=text,
            instructions=(entry.get("instructions") or "").strip(),
            section_group=(entry.get("section_group") or "").strip()[:300],
            question_type=entry.get("question_type") or GrantApplicationSection.QuestionType.NARRATIVE,
            word_limit=entry.get("word_limit") or None,
            character_limit=entry.get("character_limit") or None,
            page_limit_note=(entry.get("page_limit_note") or "").strip()[:120],
            scoring_notes=(entry.get("scoring_notes") or "").strip(),
            attachment_requirement=(entry.get("attachment_requirement") or "").strip()[:300],
            source_type=entry.get("source_type") or GrantApplicationSection.SourceType.IMPORTED,
            import_batch=batch,
            guidance=[],
        )
        created.append(section)

    _sync_attachments(application, batch, attachments)

    batch.status = GrantApplicationImport.Status.SAVED
    batch.saved_at = timezone.now()
    batch.detected_question_count = len(created)
    batch.save(update_fields=["status", "saved_at", "detected_question_count"])

    if application.status == application.Status.NOT_STARTED:
        application.status = application.Status.DRAFTING
        application.save(update_fields=["status", "updated_at"])

    return created


def _title_for(entry, index: int) -> str:
    """A short workspace label. The full question is always shown underneath."""
    explicit = (entry.get("title") or "").strip()
    if explicit:
        return explicit[:300]
    text = " ".join((entry.get("text") or "").split())
    label = (entry.get("label") or "").strip()
    prefix = f"Q{label}" if label else f"Q{index}"
    short = text if len(text) <= 70 else f"{text[:67].rstrip()}…"
    return f"{prefix}. {short}"[:300]


def _sync_attachments(application, batch, attachments) -> None:
    """Add newly-detected attachment requirements without disturbing confirmations."""
    for order, entry in enumerate(attachments, start=1):
        title = (entry.get("title") if isinstance(entry, dict) else getattr(entry, "title", "")).strip()
        if not title:
            continue
        doc_type = (
            entry.get("document_type") if isinstance(entry, dict)
            else getattr(entry, "document_type", "other")
        ) or DocumentVaultItem.DocumentType.OTHER
        requirement, created = GrantAttachmentRequirement.objects.get_or_create(
            application=application,
            title=title[:300],
            defaults={
                "document_type": doc_type,
                "order": order,
                "source_import": batch,
            },
        )
        if created:
            _link_vault_document(requirement)


def _link_vault_document(requirement) -> None:
    """Point a requirement at a matching Document Vault item when one exists.

    Reuses the vault rather than duplicating document storage — the checklist
    only tracks whether the funder's requirement is met.
    """
    if requirement.document_type == DocumentVaultItem.DocumentType.OTHER:
        return
    match = DocumentVaultItem.objects.filter(
        project=requirement.application.project,
        document_type=requirement.document_type,
    ).exclude(status=DocumentVaultItem.Status.MISSING).first()
    if match:
        requirement.linked_document = match
        requirement.save(update_fields=["linked_document", "updated_at"])


def questions_from_post(post) -> list[dict]:
    """Read the reviewed question rows back out of the review form.

    Rows the user deleted simply do not come back; rows they added arrive with
    the same field names. Ordering follows the submitted ``order`` values so
    drag-free reordering (editing the number) works.
    """
    indexes = sorted({
        key.split("-", 2)[1]
        for key in post
        if key.startswith("q-") and key.count("-") >= 2
    }, key=lambda value: int(value) if value.isdigit() else 0)

    rows: list[dict] = []
    for raw_index in indexes:
        if post.get(f"q-{raw_index}-delete") == "1":
            continue
        text = (post.get(f"q-{raw_index}-text") or "").strip()
        if not text:
            continue
        rows.append({
            "text": text,
            "label": post.get(f"q-{raw_index}-label", ""),
            "section_group": post.get(f"q-{raw_index}-section_group", ""),
            "instructions": post.get(f"q-{raw_index}-instructions", ""),
            "question_type": post.get(f"q-{raw_index}-question_type", ""),
            "required": post.get(f"q-{raw_index}-required") == "1",
            "word_limit": _positive_int(post.get(f"q-{raw_index}-word_limit")),
            "character_limit": _positive_int(post.get(f"q-{raw_index}-character_limit")),
            "page_limit_note": post.get(f"q-{raw_index}-page_limit_note", ""),
            "scoring_notes": post.get(f"q-{raw_index}-scoring_notes", ""),
            "order": _positive_int(post.get(f"q-{raw_index}-order")) or 0,
        })

    rows.sort(key=lambda row: (row["order"] or 10_000))
    return rows


def attachments_from_post(post) -> list[dict]:
    indexes = sorted({
        key.split("-", 2)[1]
        for key in post
        if key.startswith("a-") and key.count("-") >= 2
    }, key=lambda value: int(value) if value.isdigit() else 0)
    rows = []
    for raw_index in indexes:
        if post.get(f"a-{raw_index}-delete") == "1":
            continue
        title = (post.get(f"a-{raw_index}-title") or "").strip()
        if title:
            rows.append({
                "title": title,
                "document_type": post.get(f"a-{raw_index}-document_type") or "other",
            })
    return rows


def _positive_int(value) -> int | None:
    text = (value or "").strip() if isinstance(value, str) else value
    if not text:
        return None
    try:
        number = int(text)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None
