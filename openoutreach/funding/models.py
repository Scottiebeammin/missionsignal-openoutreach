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
        COMMUNITY_FOUNDATION = "community_foundation", "Community Foundation"
        CORPORATE_FOUNDATION = "corporate_foundation", "Corporate Foundation"
        FAMILY_FOUNDATION = "family_foundation", "Family Foundation"
        FEDERAL_GOVERNMENT = "federal_government", "Federal Government"
        STATE_GOVERNMENT = "state_government", "State Government"
        LOCAL_GOVERNMENT = "local_government", "Local Government"
        UNITED_WAY = "united_way", "United Way"
        WORKFORCE_BOARD = "workforce_board", "Workforce Board"
        OTHER = "other", "Other"

    name = models.CharField(max_length=500)
    funder_type = models.CharField(max_length=40, choices=FunderType.choices, default=FunderType.OTHER)
    geography = models.JSONField(default=list, blank=True)
    focus_areas = models.JSONField(default=list, blank=True)
    beneficiaries = models.JSONField(default=list, blank=True)
    eligibility_notes = models.TextField(blank=True, default="")
    website = models.URLField(max_length=500, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    active = models.BooleanField(default=True)
    external_ids = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class GovernmentEntity(models.Model):
    class EntityType(models.TextChoices):
        CITY_GOVERNMENT = "city_government", "City Government"
        COUNTY_GOVERNMENT = "county_government", "County Government"
        WORKFORCE_DEVELOPMENT_BOARD = "workforce_development_board", "Workforce Development Board"
        ECONOMIC_DEVELOPMENT_AGENCY = "economic_development_agency", "Economic Development Agency"
        PUBLIC_SCHOOL_DISTRICT = "public_school_district", "Public School District"
        PUBLIC_LIBRARY = "public_library", "Public Library"
        HOUSING_COMMUNITY_DEVELOPMENT_AGENCY = (
            "housing_community_development_agency", "Housing / Community Development Agency"
        )
        REGIONAL_PLANNING_AGENCY = "regional_planning_agency", "Regional Planning Agency"
        OTHER = "other", "Other"

    name = models.CharField(max_length=500)
    entity_type = models.CharField(max_length=60, choices=EntityType.choices, default=EntityType.OTHER)
    geography = models.JSONField(default=list, blank=True)
    focus_areas = models.JSONField(default=list, blank=True)
    department_or_office = models.CharField(max_length=300, blank=True, default="")
    opportunity_lanes = models.JSONField(default=list, blank=True)
    website = models.URLField(max_length=500, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Government entities"

    def __str__(self):
        return self.name


class ResourceProvider(models.Model):
    class ResourceType(models.TextChoices):
        TECHNICAL_ASSISTANCE_PROVIDER = "technical_assistance_provider", "Technical Assistance Provider"
        CAPACITY_BUILDING_ORGANIZATION = "capacity_building_organization", "Capacity Building Organization"
        NONPROFIT_SUPPORT_CENTER = "nonprofit_support_center", "Nonprofit Support Center"
        VOLUNTEER_NETWORK = "volunteer_network", "Volunteer Network"
        AMERICORPS_NATIONAL_SERVICE = "americorps_national_service", "AmeriCorps / National Service"
        UNIVERSITY_PROGRAM = "university_program", "University Program"
        SOFTWARE_DONATION_PROGRAM = "software_donation_program", "Software Donation Program"
        SHARED_SERVICES_PROVIDER = "shared_services_provider", "Shared Services Provider"
        EQUIPMENT_ASSISTANCE_PROGRAM = "equipment_assistance_program", "Equipment Assistance Program"
        BROADBAND_DIGITAL_ACCESS_PROGRAM = (
            "broadband_digital_access_program", "Broadband / Digital Access Program"
        )
        OTHER = "other", "Other"

    name = models.CharField(max_length=500)
    resource_type = models.CharField(max_length=60, choices=ResourceType.choices, default=ResourceType.OTHER)
    geography = models.JSONField(default=list, blank=True)
    focus_areas = models.JSONField(default=list, blank=True)
    resource_categories = models.JSONField(default=list, blank=True)
    eligibility_notes = models.TextField(blank=True, default="")
    website = models.URLField(max_length=500, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class PartnerOrganization(models.Model):
    class PartnerType(models.TextChoices):
        NONPROFIT = "nonprofit", "Nonprofit"
        UNIVERSITY_COLLEGE = "university_college", "University / College"
        COMMUNITY_COLLEGE = "community_college", "Community College"
        WORKFORCE_BOARD = "workforce_board", "Workforce Board"
        LOCAL_GOVERNMENT_AGENCY = "local_government_agency", "Local Government Agency"
        PUBLIC_LIBRARY = "public_library", "Public Library"
        SCHOOL_DISTRICT = "school_district", "School District"
        HEALTHCARE_ORGANIZATION = "healthcare_organization", "Healthcare Organization"
        CORPORATE_PARTNER = "corporate_partner", "Corporate Partner"
        FOUNDATION = "foundation", "Foundation"
        FAITH_BASED_ORGANIZATION = "faith_based_organization", "Faith-Based Organization"
        COMMUNITY_BASED_ORGANIZATION = "community_based_organization", "Community-Based Organization"
        OTHER = "other", "Other"

    name = models.CharField(max_length=500)
    partner_type = models.CharField(max_length=60, choices=PartnerType.choices, default=PartnerType.OTHER)
    geography = models.JSONField(default=list, blank=True)
    focus_areas = models.JSONField(default=list, blank=True)
    beneficiaries = models.JSONField(default=list, blank=True)
    collaboration_opportunities = models.JSONField(default=list, blank=True)
    website = models.URLField(max_length=500, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class SourceOrganization(models.Model):
    class OrganizationType(models.TextChoices):
        FOUNDATION = "foundation", "Foundation"
        GOVERNMENT_AGENCY = "government_agency", "Government Agency"
        RESOURCE_PROVIDER = "resource_provider", "Resource Provider"
        NONPROFIT = "nonprofit", "Nonprofit"
        CORPORATE_PARTNER = "corporate_partner", "Corporate Partner"
        UNIVERSITY = "university", "University"
        WORKFORCE_BOARD = "workforce_board", "Workforce Board"
        OTHER = "other", "Other"

    name = models.CharField(max_length=500, unique=True)
    organization_type = models.CharField(
        max_length=40, choices=OrganizationType.choices, default=OrganizationType.OTHER,
    )
    website = models.URLField(max_length=500, blank=True, default="")
    geography = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True, default="")
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Opportunity(models.Model):
    class OpportunityType(models.TextChoices):
        GRANT = "grant", "Grant"
        CONTRACT = "contract", "Contract"
        PARTNERSHIP = "partnership", "Partnership"
        RESOURCE = "resource", "Resource"
        SPONSORSHIP = "sponsorship", "Sponsorship"
        TRAINING = "training", "Training"
        CAPACITY_BUILDING = "capacity_building", "Capacity Building"

    class SourceType(models.TextChoices):
        FUNDER = "funder", "Funder"
        GOVERNMENT = "government", "Government"
        RESOURCE_PROVIDER = "resource_provider", "Resource Provider"
        PARTNER = "partner", "Partner"
        MANUAL = "manual", "Manual"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        UPCOMING = "upcoming", "Upcoming"
        MONITORING = "monitoring", "Monitoring"
        APPLIED = "applied", "Applied"
        WON = "won", "Won"
        ARCHIVED = "archived", "Archived"

    class PriorityLevel(models.TextChoices):
        HIGH = "high", "High"
        MEDIUM = "medium", "Medium"
        LOW = "low", "Low"

    class ValueConfidence(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    class LifecycleStatus(models.TextChoices):
        DISCOVERED = "discovered", "Discovered"
        REVIEWING = "reviewing", "Reviewing"
        QUALIFIED = "qualified", "Qualified"
        PURSUING = "pursuing", "Pursuing"
        APPLICATION_DRAFTING = "application_drafting", "Application Drafting"
        SUBMITTED = "submitted", "Submitted"
        AWARDED = "awarded", "Awarded"
        DECLINED = "declined", "Declined"
        CLOSED = "closed", "Closed"

    name = models.CharField(max_length=500)
    opportunity_type = models.CharField(
        max_length=40, choices=OpportunityType.choices, default=OpportunityType.GRANT,
    )
    source_organization = models.ForeignKey(
        SourceOrganization, null=True, blank=True, on_delete=models.SET_NULL, related_name="opportunities",
    )
    source_type = models.CharField(max_length=40, choices=SourceType.choices, default=SourceType.MANUAL)
    source_name = models.CharField(max_length=500, blank=True, default="")
    geography = models.JSONField(default=list, blank=True)
    focus_areas = models.JSONField(default=list, blank=True)
    beneficiaries = models.JSONField(default=list, blank=True)
    eligibility_notes = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    posted_date = models.DateField(null=True, blank=True)
    deadline = models.DateField(null=True, blank=True)
    priority_level = models.CharField(
        max_length=20, choices=PriorityLevel.choices, default=PriorityLevel.MEDIUM,
    )
    estimated_value = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    value_confidence = models.CharField(
        max_length=20, choices=ValueConfidence.choices, default=ValueConfidence.MEDIUM,
    )
    forecast_notes = models.TextField(blank=True, default="")
    lifecycle_status = models.CharField(
        max_length=40, choices=LifecycleStatus.choices, default=LifecycleStatus.DISCOVERED,
    )
    assigned_owner = models.ForeignKey(
        "auth.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="owned_opportunities",
    )
    lifecycle_notes = models.TextField(blank=True, default="")
    lifecycle_status_history = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class OpportunityTask(models.Model):
    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "Not Started"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETE = "complete", "Complete"
        BLOCKED = "blocked", "Blocked"

    class Priority(models.TextChoices):
        HIGH = "high", "High"
        MEDIUM = "medium", "Medium"
        LOW = "low", "Low"

    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NOT_STARTED)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    due_date = models.DateField(null=True, blank=True)
    owner = models.ForeignKey(
        "auth.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="opportunity_tasks",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("status", "due_date", "title")
        constraints = [
            models.UniqueConstraint(fields=("opportunity", "title"), name="unique_opportunity_task_title"),
        ]

    def __str__(self):
        return self.title


class OpportunityDeadline(models.Model):
    class DeadlineType(models.TextChoices):
        SUBMISSION = "submission", "Submission"
        INTERNAL_REVIEW = "internal_review", "Internal Review"
        BUDGET = "budget", "Budget"
        NARRATIVE = "narrative", "Narrative"
        ATTACHMENTS = "attachments", "Attachments"
        FOLLOW_UP = "follow_up", "Follow-up"
        REPORTING = "reporting", "Reporting"

    class Status(models.TextChoices):
        UPCOMING = "upcoming", "Upcoming"
        DUE_SOON = "due_soon", "Due Soon"
        OVERDUE = "overdue", "Overdue"
        COMPLETE = "complete", "Complete"

    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name="deadlines")
    title = models.CharField(max_length=300)
    deadline_date = models.DateField()
    deadline_type = models.CharField(
        max_length=30, choices=DeadlineType.choices, default=DeadlineType.SUBMISSION,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UPCOMING)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("deadline_date", "title")
        constraints = [
            models.UniqueConstraint(fields=("opportunity", "title"), name="unique_opportunity_deadline_title"),
        ]

    def __str__(self):
        return self.title


class DocumentVaultItem(models.Model):
    class DocumentType(models.TextChoices):
        IRS_DETERMINATION_LETTER = "irs_determination_letter", "IRS Determination Letter"
        W9 = "w9", "W-9"
        ANNUAL_BUDGET = "annual_budget", "Annual Budget"
        PROGRAM_BUDGET = "program_budget", "Program Budget"
        BOARD_LIST = "board_list", "Board List"
        STRATEGIC_PLAN = "strategic_plan", "Strategic Plan"
        ANNUAL_REPORT = "annual_report", "Annual Report"
        OUTCOME_REPORT = "outcome_report", "Outcome Report"
        AUDIT_FINANCIAL_STATEMENT = "audit_financial_statement", "Audit / Financial Statement"
        INSURANCE = "insurance", "Insurance"
        POLICY_DOCUMENT = "policy_document", "Policy Document"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        NEEDS_UPDATE = "needs_update", "Needs Update"
        MISSING = "missing", "Missing"
        ARCHIVED = "archived", "Archived"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="document_vault_items")
    title = models.CharField(max_length=300)
    document_type = models.CharField(max_length=40, choices=DocumentType.choices, default=DocumentType.OTHER)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.MISSING)
    file_reference = models.CharField(max_length=500, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    uploaded_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("document_type", "title")
        constraints = [
            models.UniqueConstraint(fields=("project", "title"), name="unique_project_document_title"),
        ]

    def __str__(self):
        return self.title


class EvidenceLibraryItem(models.Model):
    class EvidenceType(models.TextChoices):
        OUTCOME_METRIC = "outcome_metric", "Outcome Metric"
        IMPACT_STORY = "impact_story", "Impact Story"
        EVALUATION_REPORT = "evaluation_report", "Evaluation Report"
        TESTIMONIAL = "testimonial", "Testimonial"
        COMMUNITY_NEED_DATA = "community_need_data", "Community Need Data"
        PROGRAM_RESULT = "program_result", "Program Result"
        PARTNER_LETTER = "partner_letter", "Partner Letter"
        MEDIA_MENTION = "media_mention", "Media Mention"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        NEEDS_UPDATE = "needs_update", "Needs Update"
        MISSING = "missing", "Missing"
        ARCHIVED = "archived", "Archived"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="evidence_library_items")
    title = models.CharField(max_length=300)
    evidence_type = models.CharField(max_length=40, choices=EvidenceType.choices, default=EvidenceType.OTHER)
    related_program = models.CharField(max_length=300, blank=True, default="")
    metric_name = models.CharField(max_length=200, blank=True, default="")
    metric_value = models.CharField(max_length=200, blank=True, default="")
    evidence_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.MISSING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("evidence_type", "title")
        constraints = [
            models.UniqueConstraint(fields=("project", "title"), name="unique_project_evidence_title"),
        ]

    def __str__(self):
        return self.title


class OpportunityDocumentRequirement(models.Model):
    class RequirementType(models.TextChoices):
        REQUIRED_DOCUMENT = "required_document", "Required Document"
        SUPPORTING_EVIDENCE = "supporting_evidence", "Supporting Evidence"
        FINANCIAL_DOCUMENT = "financial_document", "Financial Document"
        PROGRAM_EVIDENCE = "program_evidence", "Program Evidence"
        PARTNERSHIP_EVIDENCE = "partnership_evidence", "Partnership Evidence"
        COMPLIANCE_DOCUMENT = "compliance_document", "Compliance Document"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        MISSING = "missing", "Missing"
        NEEDS_UPDATE = "needs_update", "Needs Update"
        NOT_REQUIRED = "not_required", "Not Required"

    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name="document_requirements")
    title = models.CharField(max_length=300)
    requirement_type = models.CharField(
        max_length=40, choices=RequirementType.choices, default=RequirementType.REQUIRED_DOCUMENT,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.MISSING)
    linked_document = models.ForeignKey(
        DocumentVaultItem, null=True, blank=True, on_delete=models.SET_NULL, related_name="opportunity_requirements",
    )
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("requirement_type", "title")
        constraints = [
            models.UniqueConstraint(fields=("opportunity", "title"), name="unique_opportunity_document_requirement"),
        ]

    def __str__(self):
        return self.title


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
