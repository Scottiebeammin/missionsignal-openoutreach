# openoutreach/core/models.py
from __future__ import annotations

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class SiteConfig(models.Model):
    """Singleton model for global site configuration (LLM keys, etc.)."""

    class LLMProvider(models.TextChoices):
        OPENAI = "openai", "OpenAI"
        ANTHROPIC = "anthropic", "Anthropic"
        GOOGLE = "google", "Google"
        GROQ = "groq", "Groq"
        MISTRAL = "mistral", "Mistral"
        COHERE = "cohere", "Cohere"
        OPENAI_COMPATIBLE = "openai_compatible", "OpenAI-compatible"

    llm_provider = models.CharField(
        max_length=32,
        choices=LLMProvider.choices,
        default=LLMProvider.OPENAI,
    )
    llm_api_key = models.CharField(max_length=500, blank=True, default="")
    ai_model = models.CharField(max_length=200, blank=True, default="")
    llm_api_base = models.CharField(max_length=500, blank=True, default="")

    # BetterContact email-finder key; blank disables enrichment (see emails/finder.py).
    finder_api_key = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        verbose_name = "Site Configuration"
        verbose_name_plural = "Site Configuration"

    def __str__(self):
        return "Site Configuration"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> "SiteConfig":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Campaign(models.Model):
    name = models.CharField(max_length=200, unique=True)
    users = models.ManyToManyField(User, blank=True, related_name="campaigns")
    product_docs = models.TextField(blank=True)
    campaign_objective = models.TextField(blank=True)
    booking_link = models.URLField(max_length=500, blank=True)
    is_freemium = models.BooleanField(default=False)
    action_fraction = models.FloatField(default=0.2)
    seed_public_ids = models.JSONField(default=list, blank=True)
    model_blob = models.BinaryField(null=True, blank=True)

    def __str__(self):
        return self.name


class Organization(models.Model):
    """Organization identity and analyzer-owned profile."""

    class AnalysisStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        FETCHING = "fetching", "Fetching"
        ANALYZING = "analyzing", "Analyzing"
        READY = "ready", "Ready"
        PARTIAL = "partial", "Partial"
        FAILED = "failed", "Failed"
        NEEDS_REVIEW = "needs_review", "Needs Review"

    name = models.CharField(max_length=255)
    website = models.URLField(max_length=500)
    mission = models.TextField()
    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="missionsignal_organizations",
    )

    organization_summary = models.TextField(blank=True, default="")
    organization_type = models.JSONField(null=True, blank=True, default=None)
    legal_structure = models.JSONField(null=True, blank=True, default=None)
    nonprofit_status = models.JSONField(null=True, blank=True, default=None)
    headquarters_location = models.JSONField(null=True, blank=True, default=None)
    city = models.CharField(max_length=255, blank=True, default="")
    county = models.CharField(max_length=255, blank=True, default="")
    state = models.CharField(max_length=255, blank=True, default="")
    service_area_notes = models.TextField(blank=True, default="")
    budget_range = models.CharField(max_length=100, blank=True, default="")
    current_funding_sources = models.JSONField(default=list, blank=True)
    existing_partnerships = models.JSONField(default=list, blank=True)
    service_geographies = models.JSONField(default=list, blank=True)
    focus_areas = models.JSONField(default=list, blank=True)
    beneficiaries = models.JSONField(default=list, blank=True)
    capabilities = models.JSONField(default=list, blank=True)
    outcomes_and_impact = models.JSONField(default=list, blank=True)
    aliases = models.JSONField(default=list, blank=True)
    search_keywords = models.JSONField(default=list, blank=True)

    analysis_status = models.CharField(
        max_length=20, choices=AnalysisStatus.choices, default=AnalysisStatus.PENDING,
    )
    analysis_confidence = models.FloatField(null=True, blank=True)
    analysis_warnings = models.JSONField(default=list, blank=True)
    analyzer_version = models.CharField(max_length=100, blank=True, default="")
    last_analyzed_at = models.DateTimeField(null=True, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Project(models.Model):
    """An organization initiative used to scope FundingSignal work."""

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="projects",
    )
    name = models.CharField(max_length=255)
    programs = models.TextField()
    program_summaries = models.JSONField(default=list, blank=True)
    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="missionsignal_projects",
    )
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.organization} — {self.name}"


class OrganizationMember(models.Model):
    """Binds a user to a Project with an explicit role."""

    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        EXECUTIVE_DIRECTOR = "executive_director", "Executive Director"
        DEVELOPMENT_LEAD = "development_lead", "Development Lead"
        STAFF = "staff", "Staff"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organization_memberships",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="members",
    )
    role = models.CharField(max_length=30, choices=Role.choices, default=Role.STAFF)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("user", "project"), name="unique_user_project_member"),
        ]

    def __str__(self):
        return f"{self.user} — {self.project} ({self.role})"


class TaskQuerySet(models.QuerySet):
    def pending(self):
        return self.filter(status=Task.Status.PENDING).order_by("scheduled_at")

    def claim_next(self) -> "Task | None":
        return self.pending().filter(scheduled_at__lte=timezone.now()).first()

    def seconds_to_next(self) -> float | None:
        """Seconds until the next pending task, or None if queue is empty."""
        next_task = self.pending().only("scheduled_at").first()
        if next_task is None:
            return None
        return max((next_task.scheduled_at - timezone.now()).total_seconds(), 0)


class Task(models.Model):
    class TaskType(models.TextChoices):
        CONNECT = "connect"
        CHECK_PENDING = "check_pending"
        FOLLOW_UP = "follow_up"
        EMAIL = "email"

    class Status(models.TextChoices):
        PENDING = "pending"
        RUNNING = "running"
        COMPLETED = "completed"
        FAILED = "failed"

    task_type = models.CharField(max_length=20, choices=TaskType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    scheduled_at = models.DateTimeField()
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    objects = TaskQuerySet.as_manager()

    class Meta:
        indexes = [
            models.Index(
                fields=["status", "scheduled_at"],
                name="core_task_status_sched_idx",
            ),
        ]

    def __str__(self):
        return f"{self.task_type} [{self.status}] scheduled={self.scheduled_at}"

    def mark_running(self):
        self.status = self.Status.RUNNING
        self.started_at = timezone.now()
        self.save(update_fields=["status", "started_at"])

    def mark_completed(self):
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at"])

    def mark_failed(self):
        self.status = self.Status.FAILED
        self.save(update_fields=["status"])
