from django.db import models

from openoutreach.core.models import Organization, Project


class OrganizationSourcePage(models.Model):
    class FetchStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        FETCHED = "fetched", "Fetched"
        FAILED = "failed", "Failed"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="source_pages",
    )
    url = models.URLField(max_length=1000)
    canonical_url = models.URLField(max_length=1000, blank=True, default="")
    page_type = models.CharField(max_length=50, blank=True, default="")
    title = models.CharField(max_length=500, blank=True, default="")
    raw_text = models.TextField(blank=True, default="")
    content_hash = models.CharField(max_length=64, blank=True, default="", db_index=True)
    fetch_status = models.CharField(
        max_length=20, choices=FetchStatus.choices, default=FetchStatus.PENDING,
    )
    fetched_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "url"], name="unique_organization_source_page",
            ),
        ]

    def __str__(self):
        return self.title or self.url


class OrganizationAnalysisRun(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        PARTIAL = "partial", "Partial"
        FAILED = "failed", "Failed"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="analysis_runs",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    analyzer_version = models.CharField(max_length=100, blank=True, default="")
    input_snapshot = models.JSONField(default=dict, blank=True)
    output_snapshot = models.JSONField(default=dict, blank=True)
    warnings = models.JSONField(default=list, blank=True)
    error = models.TextField(blank=True, default="")
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.organization} analysis ({self.status})"


class Celebration(models.Model):
    class CelebrationType(models.TextChoices):
        OPPORTUNITY_AWARDED = "opportunity_awarded", "Opportunity Awarded"
        OPPORTUNITY_SUBMITTED = "opportunity_submitted", "Opportunity Submitted"
        PARTNERSHIP_FORMED = "partnership_formed", "Partnership Formed"
        PROGRAM_LAUNCH = "program_launch", "Program Launch"
        FUNDING_SECURED = "funding_secured", "Funding Secured"
        IMPACT_MILESTONE = "impact_milestone", "Impact Milestone"
        VOLUNTEER_MILESTONE = "volunteer_milestone", "Volunteer Milestone"
        ORGANIZATION_MILESTONE = "organization_milestone", "Organization Milestone"
        STRATEGIC_INTRODUCTION = "strategic_introduction", "Strategic Introduction"
        COMMUNITY_COLLABORATION = "community_collaboration", "Community Collaboration"
        SUCCESS_STORY = "success_story", "Success Story"
        COMMUNITY_ACHIEVEMENT = "community_achievement", "Community Achievement"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="celebrations")
    title = models.CharField(max_length=300)
    celebration_type = models.CharField(
        max_length=40, choices=CelebrationType.choices, default=CelebrationType.ORGANIZATION_MILESTONE,
    )
    description = models.TextField(blank=True, default="")
    impact = models.TextField(blank=True, default="")
    organization_name = models.CharField(max_length=300, blank=True, default="")
    website = models.URLField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at", "title")
        constraints = [
            models.UniqueConstraint(fields=("project", "title"), name="unique_project_celebration_title"),
        ]

    def __str__(self):
        return self.title


class OrganizationContact(models.Model):
    class ContactType(models.TextChoices):
        FUNDER = "funder", "Funder"
        PROGRAM_OFFICER = "program_officer", "Program Officer"
        GOVERNMENT_CONTACT = "government_contact", "Government Contact"
        PARTNER = "partner", "Partner"
        COMMUNITY_LEADER = "community_leader", "Community Leader"
        VOLUNTEER_LEADER = "volunteer_leader", "Volunteer Leader"
        CORPORATE_CONTACT = "corporate_contact", "Corporate Contact"
        CONSULTANT = "consultant", "Consultant"
        OTHER = "other", "Other"

    class RelationshipStrength(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        WEAK = "weak", "Weak"
        DEVELOPING = "developing", "Developing"
        ESTABLISHED = "established", "Established"
        STRONG = "strong", "Strong"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="organization_contacts")
    name = models.CharField(max_length=300)
    title = models.CharField(max_length=300, blank=True, default="")
    organization = models.CharField(max_length=300, blank=True, default="")
    contact_type = models.CharField(max_length=40, choices=ContactType.choices, default=ContactType.OTHER)
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=60, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    relationship_strength = models.CharField(
        max_length=30, choices=RelationshipStrength.choices, default=RelationshipStrength.UNKNOWN,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(fields=("project", "name", "organization"), name="unique_project_contact"),
        ]

    def __str__(self):
        if self.organization:
            return f"{self.name} — {self.organization}"
        return self.name


class PartnerOrganization(models.Model):
    class PartnerType(models.TextChoices):
        FUNDING_PARTNER = "funding_partner", "Funding Partner"
        COMMUNITY_PARTNER = "community_partner", "Community Partner"
        GOVERNMENT_PARTNER = "government_partner", "Government Partner"
        CORPORATE_PARTNER = "corporate_partner", "Corporate Partner"
        ACADEMIC_PARTNER = "academic_partner", "Academic Partner"
        SERVICE_PARTNER = "service_partner", "Service Partner"
        ADVOCACY_PARTNER = "advocacy_partner", "Advocacy Partner"
        OTHER = "other", "Other"

    class RelationshipStrength(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        WEAK = "weak", "Weak"
        DEVELOPING = "developing", "Developing"
        ESTABLISHED = "established", "Established"
        STRONG = "strong", "Strong"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="relationship_partners")
    organization_name = models.CharField(max_length=300)
    partner_type = models.CharField(max_length=40, choices=PartnerType.choices, default=PartnerType.OTHER)
    relationship_strength = models.CharField(
        max_length=30, choices=RelationshipStrength.choices, default=RelationshipStrength.UNKNOWN,
    )
    notes = models.TextField(blank=True, default="")
    website = models.URLField(max_length=500, blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("organization_name",)
        constraints = [
            models.UniqueConstraint(fields=("project", "organization_name"), name="unique_project_relationship_partner"),
        ]

    def __str__(self):
        return self.organization_name
