from django.conf import settings
from django.db import models

from openoutreach.core.models import Project


def default_scoring_weights():
    return {
        "mission_program_alignment": 25,
        "eligibility_confidence": 25,
        "geography_fit": 10,
        "applicant_type_fit": 10,
        "funding_use_fit": 10,
        "award_size_fit": 5,
        "deadline_timing_fit": 10,
        "data_completeness": 5,
    }


class FundingCriteria(models.Model):
    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name="funding_criteria")
    eligible_applicant_types = models.JSONField(default=list, blank=True)
    likely_funder_types = models.JSONField(default=list, blank=True)
    likely_opportunity_types = models.JSONField(default=list, blank=True)
    focus_areas = models.JSONField(default=list, blank=True)
    beneficiaries = models.JSONField(default=list, blank=True)
    eligible_geographies = models.JSONField(default=list, blank=True)
    program_areas = models.JSONField(default=list, blank=True)
    funding_use_categories = models.JSONField(default=list, blank=True)
    likely_amount_min = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    likely_amount_max = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    deadline_horizon_days = models.PositiveIntegerField(default=365)
    inclusion_criteria = models.TextField(blank=True, default="")
    exclusion_criteria = models.TextField(blank=True, default="")
    scoring_weights = models.JSONField(default=default_scoring_weights)
    analyzer_confidence = models.FloatField(null=True, blank=True)
    source_analysis_run = models.ForeignKey(
        "signals.OrganizationAnalysisRun", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="funding_criteria",
    )
    user_reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Funding criteria for {self.project}"


class Funder(models.Model):
    class FunderType(models.TextChoices):
        GOVERNMENT = "government", "Government"
        FOUNDATION = "foundation", "Foundation"
        CORPORATE = "corporate", "Corporate"
        MULTILATERAL = "multilateral", "Multilateral"
        COMMUNITY = "community", "Community"
        OTHER = "other", "Other"

    name = models.CharField(max_length=500)
    website = models.URLField(max_length=500, blank=True, default="")
    description = models.TextField(blank=True, default="")
    funder_type = models.CharField(max_length=30, choices=FunderType.choices, default=FunderType.OTHER)
    geography = models.JSONField(default=list, blank=True)
    external_ids = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class FundingOpportunity(models.Model):
    class Status(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        UPCOMING = "upcoming", "Upcoming"
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"
        CANCELLED = "cancelled", "Cancelled"
        ARCHIVED = "archived", "Archived"

    funder = models.ForeignKey(Funder, null=True, blank=True, on_delete=models.SET_NULL, related_name="opportunities")
    identity_key = models.CharField(max_length=64, unique=True, editable=False)
    source_records = models.ManyToManyField(
        "sources.SourceRecord", through="FundingOpportunitySource",
        related_name="funding_opportunities",
    )
    title = models.CharField(max_length=500)
    summary = models.TextField(blank=True, default="")
    canonical_url = models.URLField(max_length=1000, blank=True, default="")
    external_id = models.CharField(max_length=500, blank=True, default="")
    opportunity_type = models.CharField(max_length=100, blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UNKNOWN)
    published_at = models.DateTimeField(null=True, blank=True)
    opens_at = models.DateTimeField(null=True, blank=True)
    deadline_at = models.DateTimeField(null=True, blank=True, db_index=True)
    amount_min = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    amount_max = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, blank=True, default="USD")
    total_funding_available = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    eligible_applicant_types = models.JSONField(default=list, blank=True)
    eligible_geographies = models.JSONField(default=list, blank=True)
    focus_areas = models.JSONField(default=list, blank=True)
    beneficiaries = models.JSONField(default=list, blank=True)
    requirements = models.JSONField(default=list, blank=True)
    contact_information = models.JSONField(default=dict, blank=True)
    raw_attributes = models.JSONField(default=dict, blank=True)
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.identity_key:
            from openoutreach.funding.identity import build_identity_key, normalize_canonical_url

            self.canonical_url = normalize_canonical_url(self.canonical_url)
            self.identity_key = build_identity_key(
                canonical_url=self.canonical_url,
                funder_name=self.funder.name if self.funder_id else "",
                title=self.title,
                deadline=self.deadline_at,
                opportunity_type=self.opportunity_type,
            )
        super().save(*args, **kwargs)


class FundingOpportunitySource(models.Model):
    opportunity = models.ForeignKey(
        FundingOpportunity, on_delete=models.CASCADE, related_name="source_links",
    )
    source_record = models.OneToOneField(
        "sources.SourceRecord", on_delete=models.PROTECT, related_name="funding_opportunity_link",
    )
    source_external_id = models.CharField(max_length=500, blank=True, default="")
    source_url = models.URLField(max_length=1000, blank=True, default="")
    is_primary = models.BooleanField(default=False)
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["opportunity", "source_record"], name="unique_opportunity_source_record",
            ),
        ]

    def __str__(self):
        return f"{self.opportunity}: {self.source_record}"


class FundingSignal(models.Model):
    class State(models.TextChoices):
        DISCOVERED = "discovered", "Discovered"
        NEEDS_REVIEW = "needs_review", "Needs Review"
        SHORTLISTED = "shortlisted", "Shortlisted"
        MONITORING = "monitoring", "Monitoring"
        PLANNING = "planning", "Planning"
        APPLYING = "applying", "Applying"
        SUBMITTED = "submitted", "Submitted"
        AWARDED = "awarded", "Awarded"
        DECLINED = "declined", "Declined"
        DISMISSED = "dismissed", "Dismissed"
        EXPIRED = "expired", "Expired"

    class EligibilityStatus(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        ELIGIBLE = "eligible", "Eligible"
        LIKELY_ELIGIBLE = "likely_eligible", "Likely Eligible"
        NEEDS_REVIEW = "needs_review", "Needs Review"
        INELIGIBLE = "ineligible", "Ineligible"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="funding_signals")
    opportunity = models.ForeignKey(
        FundingOpportunity, on_delete=models.CASCADE, related_name="funding_signals",
    )
    state = models.CharField(max_length=30, choices=State.choices, default=State.DISCOVERED)
    score = models.FloatField(null=True, blank=True)
    confidence = models.FloatField(null=True, blank=True)
    eligibility_status = models.CharField(
        max_length=30, choices=EligibilityStatus.choices, default=EligibilityStatus.UNKNOWN,
    )
    eligibility_reasons = models.JSONField(default=list, blank=True)
    score_breakdown = models.JSONField(default=dict, blank=True)
    explanation = models.TextField(blank=True, default="")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="owned_funding_signals",
    )
    priority = models.PositiveSmallIntegerField(default=0)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["project", "opportunity"], name="unique_project_funding_signal"),
        ]

    def __str__(self):
        return f"{self.project}: {self.opportunity}"


class FundingSignalFeedback(models.Model):
    class Label(models.TextChoices):
        GOOD_FIT = "good_fit", "Good Fit"
        BAD_FIT = "bad_fit", "Bad Fit"
        UNCERTAIN = "uncertain", "Uncertain"
        DUPLICATE = "duplicate", "Duplicate"
        INELIGIBLE = "ineligible", "Ineligible"
        OUTDATED = "outdated", "Outdated"

    signal = models.ForeignKey(FundingSignal, on_delete=models.CASCADE, related_name="feedback")
    label = models.CharField(max_length=20, choices=Label.choices)
    reason = models.TextField(blank=True, default="")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="funding_signal_feedback",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.signal}: {self.get_label_display()}"
