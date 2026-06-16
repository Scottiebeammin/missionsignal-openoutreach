from django.db import models

from openoutreach.core.models import Project
from openoutreach.sources.hashing import hash_filters


class Source(models.Model):
    class SourceType(models.TextChoices):
        MANUAL = "manual", "Manual"
        API = "api", "API"
        WEB = "web", "Web"
        RSS = "rss", "RSS"

    key = models.SlugField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    source_type = models.CharField(max_length=20, choices=SourceType.choices)
    base_url = models.URLField(max_length=500, blank=True, default="")
    active = models.BooleanField(default=True)
    configuration = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class SearchQuery(models.Model):
    class SignalType(models.TextChoices):
        FUNDING = "funding", "FundingSignal"

    class Status(models.TextChoices):
        GENERATED = "generated", "Generated"
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        ARCHIVED = "archived", "Archived"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="search_queries")
    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name="search_queries")
    signal_type = models.CharField(
        max_length=20, choices=SignalType.choices, default=SignalType.FUNDING,
    )
    query = models.TextField()
    filters = models.JSONField(default=dict, blank=True)
    filters_hash = models.CharField(max_length=64, editable=False)
    rationale = models.TextField(blank=True, default="")
    priority = models.PositiveSmallIntegerField(default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.GENERATED)
    result_count = models.PositiveIntegerField(default=0)
    generated_at = models.DateTimeField(auto_now_add=True)
    executed_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "signal_type", "source", "query", "filters_hash"],
                name="unique_project_source_query",
            ),
        ]

    def __str__(self):
        return self.query

    def save(self, *args, **kwargs):
        self.filters_hash = hash_filters(self.filters)
        update_fields = kwargs.get("update_fields")
        if update_fields is not None and "filters_hash" not in update_fields:
            kwargs["update_fields"] = {*update_fields, "filters_hash"}
        super().save(*args, **kwargs)


class SourceRecord(models.Model):
    class ProcessingStatus(models.TextChoices):
        DISCOVERED = "discovered", "Discovered"
        FETCHED = "fetched", "Fetched"
        PROCESSED = "processed", "Processed"
        FAILED = "failed", "Failed"

    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name="records")
    search_queries = models.ManyToManyField(SearchQuery, blank=True, related_name="source_records")
    external_id = models.CharField(max_length=500, blank=True, default="")
    canonical_url = models.URLField(max_length=1000, blank=True, default="")
    title = models.CharField(max_length=500, blank=True, default="")
    raw_data = models.JSONField(default=dict, blank=True)
    raw_text = models.TextField(blank=True, default="")
    content_hash = models.CharField(max_length=64, blank=True, default="", db_index=True)
    discovered_at = models.DateTimeField(auto_now_add=True)
    fetched_at = models.DateTimeField(null=True, blank=True)
    last_seen_at = models.DateTimeField(auto_now_add=True)
    processing_status = models.CharField(
        max_length=20, choices=ProcessingStatus.choices, default=ProcessingStatus.DISCOVERED,
    )
    processing_error = models.TextField(blank=True, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source", "external_id"],
                condition=~models.Q(external_id=""),
                name="unique_source_external_id",
            ),
            models.UniqueConstraint(
                fields=["source", "canonical_url"],
                condition=models.Q(external_id="", canonical_url__gt=""),
                name="unique_source_canonical_url",
            ),
        ]

    def __str__(self):
        return self.title or self.external_id or self.canonical_url or f"Source record {self.pk}"
