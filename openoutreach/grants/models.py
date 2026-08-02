"""Atlas Grant Builder — persistence.

Three models, all scoped through existing Atlas ownership:

- ``GrantApplication``  one grant draft = (project, opportunity). Permission is
  inherited from ``Project`` (the same gate every portal page uses), so a draft
  is reachable exactly when its project is.
- ``GrantApplicationSection``  one answer. Keeps the AI draft and the
  human-approved text in SEPARATE columns — AI can never silently overwrite an
  approved answer, and the UI can always tell the two apart.
- ``GrantAnswerLibraryItem``  an approved answer promoted to organization-level
  reusable knowledge, so the next application starts from what the org already
  said instead of a blank page.

Source traceability lives in ``GrantApplicationSection.source_fields`` (a JSON
list of ``{"key", "label"}``) rather than a separate join table — the same shape
this project already uses for ``score_breakdown`` / ``source_references``.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models

from openoutreach.core.models import Organization, Project
from openoutreach.funding.models import DocumentVaultItem, FundingSignal, Opportunity


class GrantApplication(models.Model):
    """A grant-writing workspace for one opportunity."""

    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "Not Started"
        DRAFTING = "drafting", "Drafting"
        NEEDS_INFORMATION = "needs_information", "Needs Information"
        READY_FOR_REVIEW = "ready_for_review", "Ready for Review"
        FINAL_REVIEW = "final_review", "Final Review"
        SUBMITTED = "submitted", "Submitted"
        AWARDED = "awarded", "Awarded"
        DECLINED = "declined", "Declined"
        WITHDRAWN = "withdrawn", "Withdrawn"

    # Statuses that mean the writing work is finished — the workspace goes
    # read-mostly and completion stops being the headline number.
    CLOSED_STATUSES = frozenset({
        Status.SUBMITTED, Status.AWARDED, Status.DECLINED, Status.WITHDRAWN,
    })

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="grant_applications")
    opportunity = models.ForeignKey(
        Opportunity, on_delete=models.CASCADE, related_name="grant_applications",
    )
    # Future-ready: the discovery pipeline's signal for this opportunity, when the
    # draft was started from a matched FundingSignal rather than the inventory row.
    funding_signal = models.ForeignKey(
        FundingSignal, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="grant_applications",
    )

    # Denormalized opportunity facts, captured when the draft is created so the
    # application still reads correctly if the inventory row is later re-scored,
    # re-imported, or archived. Never AI-generated.
    title = models.CharField(max_length=500)
    funder_name = models.CharField(max_length=500, blank=True, default="")
    deadline = models.DateField(null=True, blank=True)
    requested_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    source_url = models.URLField(max_length=1000, blank=True, default="")

    status = models.CharField(max_length=30, choices=Status.choices, default=Status.NOT_STARTED)
    notes = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="created_grant_applications",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("project", "opportunity"), name="unique_project_opportunity_grant_application",
            ),
        ]

    def __str__(self):
        return f"{self.project} — {self.title}"

    @property
    def organization(self) -> Organization:
        return self.project.organization

    @property
    def is_closed(self) -> bool:
        return self.status in self.CLOSED_STATUSES

    @property
    def requested_amount_display(self) -> str:
        """Grouped currency for templates (humanize is not installed)."""
        return f"${self.requested_amount:,.0f}" if self.requested_amount is not None else ""

    def answerable_sections(self, sections=None) -> list:
        """The sections completion is actually measured against.

        Once the real application has been imported, the standard template is no
        longer the yardstick — the funder's own questions are. Template rows are
        kept (an org may have drafted against them before importing) but they
        stop counting, so "7 of 10" always means the funder's ten questions.

        Informational and attachment questions are excluded: they are not
        answers a person writes into a box.
        """
        sections = list(self.sections.all()) if sections is None else list(sections)
        imported = [s for s in sections if s.source_type != GrantApplicationSection.SourceType.TEMPLATE]
        pool = imported or sections
        return [
            s for s in pool
            if s.question_type not in {
                GrantApplicationSection.QuestionType.INFORMATIONAL,
                GrantApplicationSection.QuestionType.ATTACHMENT,
            }
        ]

    @property
    def has_imported_questions(self) -> bool:
        return self.sections.filter(
            source_type__in=(
                GrantApplicationSection.SourceType.IMPORTED,
                GrantApplicationSection.SourceType.MANUAL,
            )
        ).exists()

    def completion_percent(self, sections=None) -> int:
        """Completion derived from real section status — never stored, never guessed.

        Approved answers count fully; a generated-but-unapproved draft counts
        half; a section Atlas knows it cannot finish yet counts a quarter (the
        work of identifying the gap is real, finishing it is not). Optional
        sections only count once they have been started, so an org is never
        penalized for skipping a section this funder didn't ask for.
        """
        sections = self.answerable_sections(sections)
        if not sections:
            return 0
        weights = {
            GrantApplicationSection.Status.APPROVED: 1.0,
            GrantApplicationSection.Status.DRAFTED: 0.5,
            GrantApplicationSection.Status.NEEDS_INFORMATION: 0.25,
            GrantApplicationSection.Status.NOT_STARTED: 0.0,
        }
        counted = [
            section for section in sections
            if section.required or section.status != GrantApplicationSection.Status.NOT_STARTED
        ]
        if not counted:
            return 0
        earned = sum(weights.get(section.status, 0.0) for section in counted)
        return round((earned / len(counted)) * 100)


class GrantApplicationImport(models.Model):
    """One paste of a real application's text, and what Atlas made of it.

    Kept as its own row so the funder's original text survives verbatim. If the
    parser gets something wrong, the source is still there to re-read — Atlas
    never has only its own interpretation of what the funder asked.
    """

    class Status(models.TextChoices):
        PARSED = "parsed", "Parsed — awaiting review"
        SAVED = "saved", "Saved to application"
        DISCARDED = "discarded", "Discarded"

    class Confidence(models.TextChoices):
        HIGH = "high", "High"
        MEDIUM = "medium", "Medium"
        LOW = "low", "Low"

    application = models.ForeignKey(
        GrantApplication, on_delete=models.CASCADE, related_name="imports",
    )
    # The paste, verbatim. Never rewritten.
    raw_text = models.TextField()
    source_label = models.CharField(
        max_length=300, blank=True, default="",
        help_text="Where the text came from, e.g. 'Foundation portal, Section 2'.",
    )
    # Application-wide rules that belong to no single question (font size, page
    # setup, eligibility statements). Kept apart so parsing can't lose them.
    application_instructions = models.JSONField(default=list, blank=True)
    parse_confidence = models.CharField(
        max_length=10, choices=Confidence.choices, default=Confidence.MEDIUM,
    )
    # Human-readable notes about what the parser was unsure of.
    parse_notes = models.JSONField(default=list, blank=True)
    detected_question_count = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PARSED)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="grant_application_imports",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    saved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"Import for {self.application_id} ({self.detected_question_count} questions)"

    @property
    def is_low_confidence(self) -> bool:
        return self.parse_confidence == self.Confidence.LOW


class GrantAttachmentRequirement(models.Model):
    """A document the funder asks to be attached, detected from the application text.

    V1.1 is a checklist: it tracks what the funder wants and lets a person
    confirm they have it. Where the organization's Document Vault already holds
    the document, ``linked_document`` points at it rather than storing a copy —
    the vault stays the single home for documents.
    """

    application = models.ForeignKey(
        GrantApplication, on_delete=models.CASCADE, related_name="attachment_requirements",
    )
    title = models.CharField(max_length=300)
    # Reuses the Document Vault's own vocabulary so a requirement can be matched
    # to a vault item instead of inventing a parallel taxonomy.
    document_type = models.CharField(
        max_length=40, choices=DocumentVaultItem.DocumentType.choices,
        default=DocumentVaultItem.DocumentType.OTHER,
    )
    linked_document = models.ForeignKey(
        DocumentVaultItem, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="grant_attachment_requirements",
    )
    confirmed = models.BooleanField(default=False)
    notes = models.TextField(blank=True, default="")
    order = models.PositiveSmallIntegerField(default=0)
    source_import = models.ForeignKey(
        GrantApplicationImport, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="attachment_requirements",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("order", "title")
        constraints = [
            models.UniqueConstraint(
                fields=("application", "title"), name="unique_application_attachment_title",
            ),
        ]

    def __str__(self):
        return self.title

    @property
    def is_satisfied(self) -> bool:
        """Confirmed by a person, or already sitting in the Document Vault."""
        if self.confirmed:
            return True
        return bool(
            self.linked_document_id
            and self.linked_document.status == DocumentVaultItem.Status.AVAILABLE
        )


class GrantApplicationSection(models.Model):
    """One answer inside a grant application.

    Two origins share this model: sections generated from Atlas's standard
    template, and questions imported verbatim from a real application. The
    difference is carried by ``source_type`` — imported rows keep the funder's
    exact wording in ``original_question``, which is never rewritten.
    """

    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "Not Started"
        NEEDS_INFORMATION = "needs_information", "Needs Information"
        DRAFTED = "drafted", "Drafted"
        APPROVED = "approved", "Approved"

    class SourceType(models.TextChoices):
        TEMPLATE = "template", "Atlas standard template"
        IMPORTED = "imported", "Imported from the real application"
        MANUAL = "manual", "Added by hand"

    class QuestionType(models.TextChoices):
        NARRATIVE = "narrative", "Narrative"
        SHORT_TEXT = "short_text", "Short text"
        LONG_TEXT = "long_text", "Long text"
        NUMERIC = "numeric", "Numeric"
        CURRENCY = "currency", "Currency"
        DATE = "date", "Date"
        YES_NO = "yes_no", "Yes / No"
        MULTIPLE_CHOICE = "multiple_choice", "Multiple choice"
        ATTACHMENT = "attachment", "Attachment"
        INFORMATIONAL = "informational", "Informational"
        UNKNOWN = "unknown", "Unknown"

    # Question types Atlas will draft prose for. Everything else is a field the
    # organization fills in itself — drafting a "Yes/No" is not a service.
    DRAFTABLE_TYPES = frozenset({
        QuestionType.NARRATIVE, QuestionType.LONG_TEXT, QuestionType.SHORT_TEXT,
        QuestionType.UNKNOWN,
    })

    application = models.ForeignKey(
        GrantApplication, on_delete=models.CASCADE, related_name="sections",
    )
    # Stable key from openoutreach.grants.services.template — survives reordering
    # and lets a future funder-specific template map onto the same answers.
    section_key = models.CharField(max_length=60)
    title = models.CharField(max_length=300)
    order = models.PositiveSmallIntegerField(default=0)
    required = models.BooleanField(default=True)

    # The funder's real question when Atlas knows it; otherwise the standard
    # template's phrasing of what this section has to answer. Editable.
    funder_question = models.TextField(blank=True, default="")
    # The imported question EXACTLY as the funder wrote it. Set once at import
    # and never rewritten — `funder_question` is the editable working copy, this
    # is the record of what was actually asked.
    original_question = models.TextField(blank=True, default="")
    guidance = models.JSONField(default=list, blank=True)

    # ── Imported-application fields (blank for standard-template sections) ──
    source_type = models.CharField(
        max_length=20, choices=SourceType.choices, default=SourceType.TEMPLATE,
    )
    question_type = models.CharField(
        max_length=20, choices=QuestionType.choices, default=QuestionType.NARRATIVE,
    )
    # The funder's own section heading, e.g. "Organization Information".
    section_group = models.CharField(max_length=300, blank=True, default="")
    # Per-question instructions printed under the question on the real form.
    instructions = models.TextField(blank=True, default="")
    # Position in the real application, preserved separately from `order` so a
    # user can reorder the workspace without losing the funder's numbering.
    imported_order = models.PositiveSmallIntegerField(default=0)
    imported_label = models.CharField(
        max_length=40, blank=True, default="",
        help_text="The funder's own numbering, e.g. '3' or 'B.2'.",
    )
    import_batch = models.ForeignKey(
        "GrantApplicationImport", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="sections",
    )
    # Reviewer/scoring guidance the funder published for this question.
    scoring_notes = models.TextField(blank=True, default="")
    # A page limit is recorded and shown, not enforced — Atlas counts words and
    # characters, and cannot know the funder's page geometry.
    page_limit_note = models.CharField(max_length=120, blank=True, default="")
    attachment_requirement = models.CharField(max_length=300, blank=True, default="")

    # AI output and human-approved text are kept apart on purpose: regeneration
    # only ever touches draft_response.
    draft_response = models.TextField(blank=True, default="")
    approved_response = models.TextField(blank=True, default="")

    word_limit = models.PositiveIntegerField(null=True, blank=True)
    character_limit = models.PositiveIntegerField(null=True, blank=True)

    status = models.CharField(max_length=30, choices=Status.choices, default=Status.NOT_STARTED)
    # [{"key": "organization.mission", "label": "Organization Mission"}, ...]
    source_fields = models.JSONField(default=list, blank=True)
    # Human-readable labels of facts Atlas does not have for this section.
    missing_information = models.JSONField(default=list, blank=True)

    last_generated_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="approved_grant_sections",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("order", "pk")
        constraints = [
            models.UniqueConstraint(
                fields=("application", "section_key"), name="unique_application_section_key",
            ),
        ]

    def __str__(self):
        return f"{self.application_id}: {self.title}"

    @property
    def current_text(self) -> str:
        """What the application actually says here — approved wins over draft."""
        return self.approved_response or self.draft_response

    @property
    def is_approved(self) -> bool:
        return self.status == self.Status.APPROVED

    @property
    def word_count(self) -> int:
        return len(self.current_text.split())

    @property
    def character_count(self) -> int:
        return len(self.current_text)

    @property
    def over_word_limit(self) -> bool:
        return bool(self.word_limit) and self.word_count > self.word_limit

    @property
    def over_character_limit(self) -> bool:
        return bool(self.character_limit) and self.character_count > self.character_limit

    @property
    def over_limit(self) -> bool:
        return self.over_word_limit or self.over_character_limit

    @property
    def limit_label(self) -> str:
        """Human counter for the editor, e.g. '1,742 / 2,000 characters'."""
        if self.character_limit:
            return f"{self.character_count:,} / {self.character_limit:,} characters"
        if self.word_limit:
            return f"{self.word_count:,} / {self.word_limit:,} words"
        return f"{self.word_count:,} words · {self.character_count:,} characters"

    # ── Imported-question helpers ──────────────────────────────────────────

    @property
    def is_imported(self) -> bool:
        return self.source_type == self.SourceType.IMPORTED

    @property
    def asked_question(self) -> str:
        """What to show the writer: the funder's exact words when we have them."""
        return self.original_question or self.funder_question

    @property
    def is_draftable_type(self) -> bool:
        """Whether drafting prose makes sense for this question type."""
        return self.question_type in self.DRAFTABLE_TYPES

    @property
    def requirement_label(self) -> str:
        """One line summarising what the funder demands, for the question header."""
        parts = ["Required" if self.required else "Optional"]
        if self.character_limit:
            parts.append(f"maximum {self.character_limit:,} characters")
        elif self.word_limit:
            parts.append(f"maximum {self.word_limit:,} words")
        if self.page_limit_note:
            parts.append(self.page_limit_note)
        return " · ".join(parts)


class GrantAnswerLibraryItem(models.Model):
    """An approved answer promoted to reusable organization knowledge."""

    class Category(models.TextChoices):
        MISSION = "mission", "Mission"
        ORGANIZATION_HISTORY = "organization_history", "Organization History"
        ORGANIZATION_OVERVIEW = "organization_overview", "Organizational Overview"
        STATEMENT_OF_NEED = "statement_of_need", "Statement of Need"
        POPULATION_SERVED = "population_served", "Population Served"
        PROGRAM_DESCRIPTION = "program_description", "Program Description"
        GOALS = "goals", "Goals"
        OUTCOMES = "outcomes", "Outcomes"
        EVALUATION_APPROACH = "evaluation_approach", "Evaluation Approach"
        ORGANIZATIONAL_CAPACITY = "organizational_capacity", "Organizational Capacity"
        PARTNERSHIPS = "partnerships", "Partnerships"
        SUSTAINABILITY = "sustainability", "Sustainability"
        EQUITY_INCLUSION = "equity_inclusion", "Equity / Inclusion Statement"
        COMMUNITY_ENGAGEMENT = "community_engagement", "Community Engagement"
        PAST_PERFORMANCE = "past_performance", "Past Performance"
        BUDGET_NARRATIVE = "budget_narrative", "Budget Narrative"
        GENERAL_OPERATING_SUPPORT = "general_operating_support", "General Operating Support"
        IMPLEMENTATION_PLAN = "implementation_plan", "Implementation Plan"
        OTHER = "other", "Other"

    class ApprovalStatus(models.TextChoices):
        APPROVED = "approved", "Approved"
        DRAFT = "draft", "Draft"
        ARCHIVED = "archived", "Archived"

    # The library is ORGANIZATION-level so answers travel across projects and
    # applications. Every read path filters on the caller's organization.
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="grant_answer_library",
    )
    project = models.ForeignKey(
        Project, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="grant_answer_library",
    )
    category = models.CharField(max_length=40, choices=Category.choices, default=Category.OTHER)
    title = models.CharField(max_length=300)
    answer = models.TextField()
    approval_status = models.CharField(
        max_length=20, choices=ApprovalStatus.choices, default=ApprovalStatus.APPROVED,
    )
    # Where this answer came from. SET_NULL so deleting an old application never
    # destroys the organization's reusable knowledge.
    source_application = models.ForeignKey(
        GrantApplication, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="library_items",
    )
    source_section = models.ForeignKey(
        GrantApplicationSection, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="library_items",
    )
    source_grant_title = models.CharField(max_length=500, blank=True, default="")
    source_fields = models.JSONField(default=list, blank=True)
    tags = models.JSONField(default=list, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="created_grant_answers",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="updated_grant_answers",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("category", "-updated_at")
        indexes = [
            models.Index(fields=["organization", "category"], name="grants_lib_org_cat_idx"),
        ]

    def __str__(self):
        return f"{self.get_category_display()}: {self.title}"

    @property
    def word_count(self) -> int:
        return len(self.answer.split())
