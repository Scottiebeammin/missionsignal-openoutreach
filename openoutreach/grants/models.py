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
from openoutreach.funding.models import FundingSignal, Opportunity


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

    def completion_percent(self, sections=None) -> int:
        """Completion derived from real section status — never stored, never guessed.

        Approved answers count fully; a generated-but-unapproved draft counts
        half; a section Atlas knows it cannot finish yet counts a quarter (the
        work of identifying the gap is real, finishing it is not). Optional
        sections only count once they have been started, so an org is never
        penalized for skipping a section this funder didn't ask for.
        """
        sections = list(self.sections.all()) if sections is None else list(sections)
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


class GrantApplicationSection(models.Model):
    """One answer inside a grant application."""

    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "Not Started"
        NEEDS_INFORMATION = "needs_information", "Needs Information"
        DRAFTED = "drafted", "Drafted"
        APPROVED = "approved", "Approved"

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
    # template's phrasing of what this section has to answer.
    funder_question = models.TextField(blank=True, default="")
    guidance = models.JSONField(default=list, blank=True)

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
