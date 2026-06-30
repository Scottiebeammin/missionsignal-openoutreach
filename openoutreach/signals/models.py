from django.db import models
from django.db.models import Q

from openoutreach.core.models import Organization, Project


class OrganizationSourcePage(models.Model):
    class FetchStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        FETCHED = "fetched", "Fetched"
        FAILED = "failed", "Failed"

    class SourceType(models.TextChoices):
        WEBSITE_PAGE = "website_page", "Website Page"
        ANNUAL_REPORT = "annual_report", "Annual Report"
        STRATEGIC_PLAN = "strategic_plan", "Strategic Plan"
        GRANT_MATERIALS = "grant_materials", "Grant Materials"
        PROGRAM_DESCRIPTION = "program_description", "Program Description"
        FUNDER_RESEARCH = "funder_research", "Funder Research"
        PARTNER_RESEARCH = "partner_research", "Partner Research"
        FOUNDER_NOTES = "founder_notes", "Founder Notes"
        OTHER = "other", "Other"

    class ReviewStatus(models.TextChoices):
        NEW = "new", "New"
        NEEDS_REVIEW = "needs_review", "Needs Review"
        REVIEWED = "reviewed", "Reviewed"
        USED_IN_SNAPSHOT = "used_in_snapshot", "Used In Snapshot"
        ARCHIVED = "archived", "Archived"

    class Relevance(models.TextChoices):
        HIGH = "high", "High"
        MEDIUM = "medium", "Medium"
        LOW = "low", "Low"
        UNKNOWN = "unknown", "Unknown"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="source_pages",
    )
    project = models.ForeignKey(
        Project, null=True, blank=True, on_delete=models.CASCADE, related_name="source_materials",
    )
    url = models.URLField(max_length=1000, blank=True, default="")
    canonical_url = models.URLField(max_length=1000, blank=True, default="")
    page_type = models.CharField(max_length=50, blank=True, default="")
    source_type = models.CharField(
        max_length=40, choices=SourceType.choices, default=SourceType.WEBSITE_PAGE,
    )
    title = models.CharField(max_length=500, blank=True, default="")
    raw_text = models.TextField(blank=True, default="")
    notes = models.TextField(blank=True, default="")
    relevance = models.CharField(max_length=20, choices=Relevance.choices, default=Relevance.UNKNOWN)
    review_status = models.CharField(
        max_length=30, choices=ReviewStatus.choices, default=ReviewStatus.NEW,
    )
    content_hash = models.CharField(max_length=64, blank=True, default="", db_index=True)
    fetch_status = models.CharField(
        max_length=20, choices=FetchStatus.choices, default=FetchStatus.PENDING,
    )
    fetched_at = models.DateTimeField(null=True, blank=True)
    last_reviewed_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "url"],
                condition=~Q(url=""),
                name="unique_organization_source_page",
            ),
        ]

    def __str__(self):
        return self.title or self.url or self.get_source_type_display()


class InterestSignup(models.Model):
    class InterestType(models.TextChoices):
        OPPORTUNITY_WEB_SNAPSHOT = "opportunity_web_snapshot", "Get Opportunity Web Snapshot"
        FOUNDING_ATLAS_PARTNERS = "founding_atlas_partners", "Join Founding Atlas Partners"
        NEWSLETTER_UPDATES = "newsletter_updates", "Newsletter / Updates"
        PARTNERSHIP_INQUIRY = "partnership_inquiry", "Partnership Inquiry"
        QUESTION = "question", "Question / Request Info"

    class Status(models.TextChoices):
        NEW = "new", "New"
        REVIEWED = "reviewed", "Reviewed"
        CONTACTED = "contacted", "Contacted"
        CONVERTED = "converted", "Converted"
        ARCHIVED = "archived", "Archived"

    name = models.CharField(max_length=300)
    organization = models.CharField(max_length=300)
    email = models.EmailField()
    role = models.CharField(max_length=300, blank=True, default="")
    website = models.URLField(max_length=500, blank=True, default="")
    interest_type = models.CharField(
        max_length=40,
        choices=InterestType.choices,
        default=InterestType.OPPORTUNITY_WEB_SNAPSHOT,
    )
    message = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    nurture_step = models.PositiveSmallIntegerField(default=0)
    research_brief = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "organization", "name")

    def __str__(self):
        return f"{self.organization} — {self.email}"


class SalesLead(models.Model):
    class Source(models.TextChoices):
        WARM = "warm", "Warm"
        COLD = "cold", "Cold"
        REFERRAL = "referral", "Referral"
        INBOUND = "inbound", "Inbound (Waitlist)"

    class Status(models.TextChoices):
        NEW = "new", "New"
        REACHED_OUT = "reached_out", "Reached Out"
        CALL_SCHEDULED = "call_scheduled", "Call Scheduled"
        CALL_DONE = "call_done", "Call Done"
        CLOSED = "closed", "Closed — Won"
        NURTURING = "nurturing", "Nurturing"
        PASSED = "passed", "Passed"

    name = models.CharField(max_length=300)
    organization = models.CharField(max_length=300, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=50, blank=True, default="")
    role = models.CharField(max_length=200, blank=True, default="")
    linkedin_url = models.URLField(max_length=500, blank=True, default="")
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.WARM)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    notes = models.TextField(blank=True, default="")
    outreach_draft = models.TextField(blank=True, default="")
    next_follow_up = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("status", "-updated_at")

    def __str__(self):
        return f"{self.name} — {self.organization}"


class PilotProfile(models.Model):
    class LifecycleStatus(models.TextChoices):
        WAITLIST = "waitlist", "Waitlist"
        QUALIFIED = "qualified", "Qualified"
        INVITED = "invited", "Invited"
        QUESTIONNAIRE_SENT = "questionnaire_sent", "Discovery Sent"
        QUESTIONNAIRE_COMPLETED = "questionnaire_completed", "Discovery Completed"
        SNAPSHOT_IN_PROGRESS = "snapshot_in_progress", "Snapshot In Progress"
        SNAPSHOT_DELIVERED = "snapshot_delivered", "Snapshot Delivered"
        WALKTHROUGH_SCHEDULED = "walkthrough_scheduled", "Walkthrough Scheduled"
        ACTIVE_PILOT = "active_pilot", "Active Pilot"
        PILOT_COMPLETE = "pilot_complete", "Pilot Complete"

    class SnapshotStatus(models.TextChoices):
        INTAKE_COMPLETE = "intake_complete", "Intake Complete"
        REVIEWING_ORGANIZATION = "reviewing_organization", "Reviewing Organization"
        BUILDING_OPPORTUNITY_WEB = "building_opportunity_web", "Building Opportunity Web"
        BUILDING_SNAPSHOT = "building_snapshot", "Building Snapshot"
        INTERNAL_REVIEW = "internal_review", "Internal Review"
        READY_FOR_DELIVERY = "ready_for_delivery", "Ready For Delivery"
        DELIVERED = "delivered", "Delivered"

    class WalkthroughStatus(models.TextChoices):
        NOT_SCHEDULED = "not_scheduled", "Not Scheduled"
        REQUESTED = "requested", "Requested"
        SCHEDULED = "scheduled", "Scheduled"
        COMPLETED = "completed", "Completed"

    signup = models.OneToOneField(
        InterestSignup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pilot_profile",
    )
    project = models.OneToOneField(
        Project,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="pilot_profile",
    )

    organization_name = models.CharField(max_length=300)
    contact_name = models.CharField(max_length=300, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    website = models.URLField(max_length=500, blank=True, default="")

    lifecycle_status = models.CharField(
        max_length=40,
        choices=LifecycleStatus.choices,
        default=LifecycleStatus.WAITLIST,
    )

    mission = models.TextField(blank=True, default="")
    location = models.CharField(max_length=300, blank=True, default="")
    year_founded = models.CharField(max_length=50, blank=True, default="")
    annual_budget_range = models.CharField(max_length=100, blank=True, default="")
    team_size = models.CharField(max_length=100, blank=True, default="")

    primary_programs = models.TextField(blank=True, default="")
    communities_served = models.TextField(blank=True, default="")
    current_initiatives = models.TextField(blank=True, default="")
    geographic_reach = models.TextField(blank=True, default="")

    current_revenue_sources = models.TextField(blank=True, default="")
    grant_experience = models.TextField(blank=True, default="")
    major_funders = models.TextField(blank=True, default="")
    fundraising_activities = models.TextField(blank=True, default="")
    funding_challenges = models.TextField(blank=True, default="")

    key_partners = models.TextField(blank=True, default="")
    community_relationships = models.TextField(blank=True, default="")
    strategic_relationships = models.TextField(blank=True, default="")
    government_relationships = models.TextField(blank=True, default="")
    corporate_relationships = models.TextField(blank=True, default="")

    top_goals = models.TextField(blank=True, default="")
    biggest_challenges = models.TextField(blank=True, default="")
    desired_outcomes = models.TextField(blank=True, default="")
    success_definition = models.TextField(blank=True, default="")

    strategic_plan = models.FileField(upload_to="pilot_documents/", blank=True, default="")
    annual_report = models.FileField(upload_to="pilot_documents/", blank=True, default="")
    grant_materials = models.FileField(upload_to="pilot_documents/", blank=True, default="")
    program_information = models.FileField(upload_to="pilot_documents/", blank=True, default="")
    other_documents = models.FileField(upload_to="pilot_documents/", blank=True, default="")
    document_notes = models.TextField(blank=True, default="")

    snapshot_status = models.CharField(
        max_length=40,
        choices=SnapshotStatus.choices,
        default=SnapshotStatus.REVIEWING_ORGANIZATION,
    )
    assigned_reviewer = models.CharField(max_length=300, blank=True, default="")
    snapshot_notes = models.TextField(blank=True, default="")
    snapshot_link = models.URLField(max_length=500, blank=True, default="")
    snapshot_delivery_date = models.DateField(null=True, blank=True)
    internal_comments = models.TextField(blank=True, default="")

    walkthrough_status = models.CharField(
        max_length=30,
        choices=WalkthroughStatus.choices,
        default=WalkthroughStatus.NOT_SCHEDULED,
    )
    meeting_date = models.DateTimeField(null=True, blank=True)
    meeting_notes = models.TextField(blank=True, default="")
    follow_up_actions = models.TextField(blank=True, default="")
    recommended_next_steps = models.TextField(blank=True, default="")

    action_plan_started = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("organization_name", "email")

    def __str__(self):
        return f"{self.organization_name} pilot"


class PilotFeedback(models.Model):
    class Recommendation(models.TextChoices):
        YES = "yes", "Yes"
        MAYBE = "maybe", "Maybe"
        NO = "no", "No"

    pilot = models.OneToOneField(PilotProfile, on_delete=models.CASCADE, related_name="feedback")
    most_valuable = models.TextField()
    confusing = models.TextField(blank=True, default="")
    indispensable = models.TextField(blank=True, default="")
    would_recommend = models.CharField(
        max_length=20,
        choices=Recommendation.choices,
        default=Recommendation.MAYBE,
    )
    additional_feedback = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"Pilot feedback — {self.pilot.organization_name}"


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
    geography = models.JSONField(default=list, blank=True)
    relationship_strength = models.CharField(
        max_length=30, choices=RelationshipStrength.choices, default=RelationshipStrength.UNKNOWN,
    )
    notes = models.TextField(blank=True, default="")
    mission_alignment_notes = models.TextField(blank=True, default="")
    opportunity_notes = models.TextField(blank=True, default="")
    relationship_notes = models.TextField(blank=True, default="")
    source_references = models.JSONField(default=list, blank=True)
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
