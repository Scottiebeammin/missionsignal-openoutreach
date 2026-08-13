from django.conf import settings
from django.db import models
from django.utils import timezone
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



class DispositionReason(models.TextChoices):
    """Why a prospect is under review or out of a campaign.

    Split into two sets below (``AUTO_DISQUALIFY`` / everything else) because
    negative evidence does not all mean the same thing. "The organization closed"
    is a fact that settles the question; "sources disagree about who runs it" is a
    reason for a human to look, not to reject. Turning uncertainty into rejection
    quietly shrinks the list and nobody notices.
    """

    ORGANIZATION_CLOSED = "organization_closed", "Organization closed"
    ORGANIZATION_INACTIVE = "organization_inactive", "Organization inactive"
    WRONG_ORGANIZATION_TYPE = "wrong_organization_type", "Wrong organization type"
    WRONG_GEOGRAPHY = "wrong_geography", "Outside campaign geography"
    ALREADY_CUSTOMER = "already_customer", "Already a customer"
    ALREADY_SUPPRESSED = "already_suppressed", "Suppressed / do-not-contact"
    OUTSIDE_CAMPAIGN_CRITERIA = "outside_campaign_criteria", "Outside campaign criteria"

    CONTACT_LEFT_ORGANIZATION = "contact_left_organization", "Contact left the organization"
    CONTACT_ROLE_INAPPROPRIATE = "contact_role_inappropriate", "Contact role inappropriate"
    DUPLICATE_EXISTING_RELATIONSHIP = "duplicate_existing_relationship", "Duplicate of an existing relationship"
    INSUFFICIENT_RELEVANCE = "insufficient_relevance", "Campaign proposition not relevant"
    CONFLICTING_RESEARCH = "conflicting_research", "Sources conflict"
    STALE_RESEARCH = "stale_research", "Research too old to act on"
    NEEDS_HUMAN_REVIEW = "needs_human_review", "Needs human review"


#: Reasons that are a settled, present-tense fact about the organization and so may
#: exclude it from a campaign without a human. Everything else routes to REVIEW.
#: Note what is NOT here: contact problems (they belong to the contact, not the org),
#: weak relevance (category-relevant outreach is legitimate), and anything derived from
#: stale or conflicting sources.
AUTO_DISQUALIFY_REASONS = frozenset({
    DispositionReason.ORGANIZATION_CLOSED,
    DispositionReason.ORGANIZATION_INACTIVE,
    DispositionReason.WRONG_ORGANIZATION_TYPE,
    DispositionReason.WRONG_GEOGRAPHY,
    DispositionReason.ALREADY_CUSTOMER,
    DispositionReason.ALREADY_SUPPRESSED,
    DispositionReason.OUTSIDE_CAMPAIGN_CRITERIA,
})

#: Reasons that are about the person, not the institution. A departed ED does not
#: close a charity — the organization stays reachable through someone else.
CONTACT_SCOPED_REASONS = frozenset({
    DispositionReason.CONTACT_LEFT_ORGANIZATION,
    DispositionReason.CONTACT_ROLE_INAPPROPRIATE,
})


def disposition_for(reason: str, *, evidence_is_current: bool = True) -> tuple[str, str]:
    """Map a reason code to (disposition, scope) — the deterministic half of gap 2.

    ``evidence_is_current=False`` downgrades any would-be disqualification to review:
    a historically accurate fact is not grounds for a present-tense exclusion, and an
    organization wrongly dropped on stale evidence is never looked at again.
    """
    reason = (reason or "").strip().lower()
    scope = ("contact" if reason in CONTACT_SCOPED_REASONS else "organization")
    if reason in AUTO_DISQUALIFY_REASONS and evidence_is_current:
        return "disqualified", scope
    if not reason:
        return "eligible", scope
    return "review", scope


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

    class Segment(models.TextChoices):
        WARM = "warm", "Warm Network"
        COLD_FLORIDA_CRM = "cold_florida_crm", "Cold — Florida CRM"
        COLD_CALL_LIST = "cold_call_list", "Cold — Call List"  # phone/website, no email

    class Warmth(models.TextChoices):
        HOT = "hot", "Hot"
        WARM = "warm", "Warm"
        RECONNECT = "reconnect", "Reconnect"
        COLD = "cold", "Cold"

    class Outcome(models.TextChoices):
        # What happened AFTER an outreach email went out. Blank = not sent yet.
        AWAITING = "awaiting", "Awaiting reply"
        REPLIED = "replied", "Replied"
        INTERESTED = "interested", "Interested"
        MEETING = "meeting", "Meeting booked"
        NOT_INTERESTED = "not_interested", "Not interested"
        BOUNCED = "bounced", "Bounced / bad email"

    name = models.CharField(max_length=300)
    organization = models.CharField(max_length=300, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    # Additional people to add to the email thread (comma-separated). CC'd on
    # every outreach send to this lead.
    cc_emails = models.CharField(max_length=500, blank=True, default="")
    phone = models.CharField(max_length=50, blank=True, default="")
    role = models.CharField(max_length=200, blank=True, default="")
    linkedin_url = models.URLField(max_length=500, blank=True, default="")
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.WARM)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    list_segment = models.CharField(max_length=20, choices=Segment.choices, default=Segment.WARM)
    warmth = models.CharField(max_length=20, choices=Warmth.choices, blank=True, default="")
    region = models.CharField(max_length=120, blank=True, default="")
    focus_area = models.CharField(max_length=200, blank=True, default="")
    why_fit = models.TextField(blank=True, default="")
    subject_line = models.CharField(max_length=300, blank=True, default="")
    email_status = models.CharField(max_length=30, blank=True, default="not_sent")
    # Reply/response tracking — set to AWAITING on send, then the operator logs
    # what came back. Blank until the lead is contacted.
    outreach_outcome = models.CharField(max_length=20, choices=Outcome.choices, blank=True, default="")
    # ── Three kinds of text, three levels of authority ───────────────────────
    # `notes` used to hold all of them at once — researched profile, archived
    # prior emails, and whatever the operator typed — and `_lead_facts` handed the
    # whole blob to the writer under "Notes:". So "probably short-staffed" could
    # come back as "with your staffing challenges". These separate that.
    #
    # LEGACY. Operator notes from before the split, plus anything written by code
    # that predates it. Never sent to the writer as fact. Kept, not migrated:
    # guessing which sentences in an old mixed blob were research would be exactly
    # the silent reinterpretation this split exists to prevent.
    notes = models.TextField(
        blank=True, default="",
        help_text="Legacy mixed notes. Not used as writer evidence — see research_profile.")
    # Verified, sourced research about the organization. The ONLY prose field that
    # reaches the writer as fact.
    research_profile = models.TextField(
        blank=True, default="",
        help_text="Verified research, approved for use as recipient evidence in copy.")
    # Human workflow commentary: "call Marcus first", "website looked stale",
    # "probably not a fit". Operational, not factual. Never reaches the writer.
    operator_notes = models.TextField(
        blank=True, default="",
        help_text="Operator commentary. Workflow only — never treated as a fact about the org.")
    # Genuine shared history, approved for warm outreach. Reaches the writer, but
    # in its own labelled section so it is never mistaken for researched fact.
    relationship_context = models.TextField(
        blank=True, default="",
        help_text="Approved relationship history for warm outreach — a separate authority "
                  "level from research, passed to the writer under its own heading.")

    # ── Campaign disposition ─────────────────────────────────────────────────
    # Campaign-scoped, deliberately: "not a fit for this campaign" is not
    # "never contact again". Global suppression stays in EmailOptOut.
    DISPOSITION_ELIGIBLE = "eligible"
    DISPOSITION_REVIEW = "review"
    DISPOSITION_DISQUALIFIED = "disqualified"
    DISPOSITION_CHOICES = [
        (DISPOSITION_ELIGIBLE, "Eligible"),
        (DISPOSITION_REVIEW, "Needs review"),
        (DISPOSITION_DISQUALIFIED, "Disqualified from this campaign"),
    ]
    disposition = models.CharField(
        max_length=20, choices=DISPOSITION_CHOICES, default=DISPOSITION_ELIGIBLE, db_index=True)
    disposition_reason = models.CharField(
        max_length=40, choices=DispositionReason.choices, blank=True, default="",
        help_text="Machine-readable reason — queryable, so exclusions can be audited.")
    disposition_detail = models.TextField(
        blank=True, default="", help_text="Human-readable explanation and its evidence.")
    disposition_scope = models.CharField(
        max_length=20, blank=True, default="",
        help_text="'organization' or 'contact'. A departed contact does not close the org.")
    disposition_source = models.CharField(
        max_length=20, blank=True, default="",
        help_text="'automatic' or 'human' — whether a person confirmed this.")
    disposition_at = models.DateTimeField(null=True, blank=True)
    # When the evidence behind the disposition was gathered. A disqualification
    # resting on old evidence is downgraded to review rather than trusted.
    evidence_as_of = models.DateField(null=True, blank=True)

    outreach_draft = models.TextField(blank=True, default="")
    next_follow_up = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("status", "-updated_at")

    def __str__(self):
        return f"{self.name} — {self.organization}"

    def cold_outreach_block(self) -> str:
        """Why cold outreach must not go to this lead right now, or "" if it may.

        The single source of truth. Called from the send path — the one place every
        send goes through — and again at drafting for defence in depth. Returning a
        reason string rather than a bool so the caller can say what happened; a
        silent skip is how a batch quietly shrinks and nobody asks why.
        """
        if self.disposition == self.DISPOSITION_DISQUALIFIED:
            reason = self.get_disposition_reason_display() if self.disposition_reason else "no reason recorded"
            return f"disqualified from this campaign ({reason})"
        if self.disposition == self.DISPOSITION_REVIEW:
            reason = self.get_disposition_reason_display() if self.disposition_reason else "no reason recorded"
            return f"held for human review ({reason})"
        if self.status == self.Status.PASSED:
            return "retired by the operator (status: passed)"
        # Terminal outcomes: states that end the acquisition sequence. These are
        # deliberately distinct from the concepts around them — opt-out is global
        # suppression (EmailOptOut), disqualification is campaign fit; this is
        # "the sequence reached its end, one way or the other". Before this,
        # outreach_outcome controlled nothing: a lead who said no could be drafted
        # and sent to again.
        if self.outreach_outcome == self.Outcome.NOT_INTERESTED:
            return "declined (outcome: not interested) — the acquisition sequence is over"
        if self.outreach_outcome == self.Outcome.MEETING:
            return ("in conversation (outcome: meeting booked) — acquisition outreach is done; "
                    "anything further is relationship mail, not the cold sequence")
        if self.outreach_outcome == self.Outcome.BOUNCED:
            return "address bounced — do not resend to a dead address"
        if self.status == self.Status.CLOSED:
            return "closed-won — a customer, not an acquisition target"
        return ""

    def followup_hold(self) -> str:
        """Why AUTOMATED follow-up drafting should pause, or "" if it may proceed.

        Weaker than ``cold_outreach_block`` on purpose: a reply or expressed
        interest means a live conversation, which a human (or a future
        reply-classification layer) should resolve — an automated cold follow-up
        into an open thread reads as nobody-home. But it is not suppression and
        not disqualification, so a human may still write and send by hand; only
        the automated drafting path holds.
        """
        if self.outreach_outcome in (self.Outcome.REPLIED, self.Outcome.INTERESTED):
            return (f"conversation open (outcome: {self.get_outreach_outcome_display()}) — "
                    "resolve the thread by hand rather than automating into it")
        return ""

    def set_disposition(self, reason: str, *, detail: str = "", source: str = "automatic",
                        evidence_as_of=None, evidence_is_current: bool = True):
        """Apply a reason code through the deterministic mapping and stamp the audit trail.

        Never decides for itself: ``disposition_for`` owns which reasons exclude and
        which only flag, so the same reason cannot mean different things in different
        callers.
        """
        disposition, scope = disposition_for(reason, evidence_is_current=evidence_is_current)
        self.disposition = disposition
        self.disposition_reason = reason
        self.disposition_detail = detail
        self.disposition_scope = scope
        self.disposition_source = source
        self.disposition_at = timezone.now()
        if evidence_as_of is not None:
            self.evidence_as_of = evidence_as_of
        return self


class FloridaOrg(models.Model):
    """One row of the statewide Florida IRS exempt-org universe (114k+).

    These are NOT leads — they're the prospect universe. Promoting one to the
    sales pipeline creates a SalesLead and links it via `promoted_lead`.
    """

    record_id = models.CharField(max_length=20, unique=True)  # e.g. NP-000001
    ein = models.CharField(max_length=20, db_index=True)
    name = models.CharField(max_length=300)
    sort_name = models.CharField(max_length=300, blank=True, default="")
    street = models.CharField(max_length=300, blank=True, default="")
    city = models.CharField(max_length=120, blank=True, default="")
    county = models.CharField(max_length=120, blank=True, default="", db_index=True)
    region = models.CharField(max_length=120, blank=True, default="", db_index=True)
    state = models.CharField(max_length=10, blank=True, default="")
    zip_code = models.CharField(max_length=20, blank=True, default="")
    subsection = models.CharField(max_length=10, blank=True, default="")
    ntee_code = models.CharField(max_length=20, blank=True, default="")
    ntee_sector = models.CharField(max_length=120, blank=True, default="", db_index=True)
    service_area = models.CharField(max_length=60, blank=True, default="", db_index=True)
    ruling_month = models.CharField(max_length=10, blank=True, default="")
    asset_amount = models.BigIntegerField(null=True, blank=True)
    income_amount = models.BigIntegerField(null=True, blank=True)
    priority = models.CharField(max_length=20, blank=True, default="", db_index=True)
    relationship_stage = models.CharField(max_length=60, blank=True, default="")
    next_action = models.CharField(max_length=300, blank=True, default="")
    website = models.URLField(max_length=500, blank=True, default="")
    phone = models.CharField(max_length=40, blank=True, default="")
    contact_email = models.EmailField(blank=True, default="")
    principal_officer = models.CharField(max_length=200, blank=True, default="")
    contact_source = models.CharField(max_length=200, blank=True, default="")
    contact_updated_at = models.DateTimeField(null=True, blank=True)
    promoted_lead = models.ForeignKey(
        SalesLead, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="florida_orgs",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return f"{self.record_id} — {self.name}"


class CountyRollout(models.Model):
    """County-by-county rollout board for the Florida market (67 counties)."""

    county = models.CharField(max_length=120, unique=True)
    rollout_tier = models.CharField(max_length=60, blank=True, default="")
    region = models.CharField(max_length=120, blank=True, default="")
    owner = models.CharField(max_length=120, blank=True, default="")
    status = models.CharField(max_length=60, blank=True, default="")
    nonprofit_count = models.IntegerField(default=0)
    high_priority_count = models.IntegerField(default=0)
    funder_starter_count = models.IntegerField(default=0)
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ("county",)

    def __str__(self):
        return self.county


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


class MatchFeedback(models.Model):
    """Client verdict on a recommended match ("not a fit" for now).

    ``target_key`` is the Opportunity pk as a string for kind=opportunity, or the
    record name for reference matches (funder/partner/resource/government), since
    those surface as name-keyed score dataclasses rather than per-project rows.
    Suppression happens at the view layer — see openoutreach/signals/feedback.py.
    """

    class Kind(models.TextChoices):
        OPPORTUNITY = "opportunity", "Opportunity"
        FUNDER = "funder", "Funder"
        PARTNER = "partner", "Partner"
        RESOURCE = "resource", "Resource"
        GOVERNMENT = "government", "Government"

    class Verdict(models.TextChoices):
        NOT_A_FIT = "not_a_fit", "Not a fit"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="match_feedback")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    target_key = models.CharField(max_length=300, db_index=True)
    verdict = models.CharField(max_length=20, choices=Verdict.choices, default=Verdict.NOT_A_FIT)
    note = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="match_feedback",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("project", "kind", "target_key"), name="unique_project_match_feedback",
            ),
        ]

    def __str__(self):
        return f"{self.project_id} — {self.kind}:{self.target_key} ({self.verdict})"


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


class EmailOptOut(models.Model):
    """An address that has asked not to be contacted again.

    Kept separate from SalesLead deliberately: an opt-out belongs to the *person*,
    not to a row in one pipeline. The same address can appear on several leads, or
    be re-imported later from a fresh market pull, and it must stay suppressed
    through all of it. Checked in `send_outreach_email`, which every send goes
    through.
    """

    email = models.EmailField(unique=True)
    source = models.CharField(max_length=40, default="link",
                              help_text="How it was recorded: link, reply, manual.")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Email opt-out"

    def __str__(self):
        return self.email


class OutreachAngle(models.TextChoices):
    """Why the recipient might care — the *reason*, not the source database.

    Tracked so a follow-up can mechanically tell whether it is introducing a new
    reason or paraphrasing the first touch. Before this existed the only record of
    a previous message was its prose, archived into ``SalesLead.notes``, which made
    "is this actually a new angle?" a judgement call nobody could audit.

    Grouped into families (see ``ANGLE_FAMILY``) because a shift *between* families
    — county funding to free technical assistance, contract expiry to readiness — is
    a materially different reason to care, while two funding angles are a smaller
    move. Atlas surfaces funding, partnerships, government pathways, free and
    low-cost resources, technical assistance and readiness; the taxonomy has to be
    wide enough to hold all of that or every email collapses back onto funding.

    Not enforced by a DB constraint, so a new value costs no migration.
    """

    # ── Funding ──────────────────────────────────────────────────────────────
    FEDERAL_FUNDING = "federal_funding", "Federal funding"
    FEDERAL_PROGRAM_PATHWAY = "federal_program_pathway", "Federal program pathway"
    GRANTS_GOV_MATCH = "grants_gov_match", "Grants.gov match"
    STATE_FUNDING = "state_funding", "State funding"
    COUNTY_FUNDING = "county_funding", "County funding"
    CITY_FUNDING = "city_funding", "City funding"
    AGENCY_PROGRAM = "agency_program", "Agency program"
    CONTRACT_EXPIRATION = "contract_expiration", "Contract expiration"
    INTERMEDIARY_STRUCTURE = "intermediary_structure", "Intermediary structure"
    PROCUREMENT_PATHWAY = "procurement_pathway", "Procurement pathway"

    # ── Partnerships and government pathways ─────────────────────────────────
    PARTNERSHIP_PATHWAY = "partnership_pathway", "Partnership pathway"
    COMMUNITY_PARTNER_RESOURCE = "community_partner_resource", "Community partner resource"
    GOVERNMENT_REFERRAL_PATHWAY = "government_referral_pathway", "Government referral pathway"
    AGENCY_RELATIONSHIP = "agency_relationship", "Agency relationship"
    INSTITUTIONAL_PARTNER = "institutional_partner", "Institutional partner"

    # ── Free / lower-cost resources ──────────────────────────────────────────
    FREE_RESOURCE = "free_resource", "Free resource"
    LOW_COST_RESOURCE = "low_cost_resource", "Low-cost resource"
    TECHNICAL_ASSISTANCE = "technical_assistance", "Technical assistance"
    CAPACITY_BUILDING_RESOURCE = "capacity_building_resource", "Capacity-building resource"
    TRAINING_RESOURCE = "training_resource", "Training resource"
    TECHNOLOGY_RESOURCE = "technology_resource", "Technology resource"
    FACILITY_OR_SPACE_RESOURCE = "facility_or_space_resource", "Facility or space resource"
    WORKFORCE_RESOURCE = "workforce_resource", "Workforce resource"
    VOLUNTEER_RESOURCE = "volunteer_resource", "Volunteer resource"
    IN_KIND_RESOURCE = "in_kind_resource", "In-kind resource"
    DATA_OR_RESEARCH_RESOURCE = "data_or_research_resource", "Data or research resource"

    # ── Readiness and operational value ──────────────────────────────────────
    READINESS_GAP = "readiness_gap", "Readiness gap"
    APPLICATION_READINESS = "application_readiness", "Application readiness"
    COMPLIANCE_READINESS = "compliance_readiness", "Compliance readiness"
    FRAGMENTED_RESEARCH = "fragmented_research", "Fragmented research"
    CATEGORY_MECHANISM = "category_mechanism", "Category-level mechanism"
    SCHOOL_SPECIFIC_RESOURCE = "school_specific_resource", "School-specific resource"

    UNCLASSIFIED = "unclassified", "Unclassified"


ANGLE_FAMILY: dict[str, str] = {
    **{a: "funding" for a in (
        OutreachAngle.FEDERAL_FUNDING, OutreachAngle.FEDERAL_PROGRAM_PATHWAY,
        OutreachAngle.GRANTS_GOV_MATCH, OutreachAngle.STATE_FUNDING,
        OutreachAngle.COUNTY_FUNDING, OutreachAngle.CITY_FUNDING,
        OutreachAngle.AGENCY_PROGRAM, OutreachAngle.CONTRACT_EXPIRATION,
        OutreachAngle.INTERMEDIARY_STRUCTURE, OutreachAngle.PROCUREMENT_PATHWAY,
    )},
    **{a: "partnership" for a in (
        OutreachAngle.PARTNERSHIP_PATHWAY, OutreachAngle.COMMUNITY_PARTNER_RESOURCE,
        OutreachAngle.GOVERNMENT_REFERRAL_PATHWAY, OutreachAngle.AGENCY_RELATIONSHIP,
        OutreachAngle.INSTITUTIONAL_PARTNER,
    )},
    **{a: "resource" for a in (
        OutreachAngle.FREE_RESOURCE, OutreachAngle.LOW_COST_RESOURCE,
        OutreachAngle.TECHNICAL_ASSISTANCE, OutreachAngle.CAPACITY_BUILDING_RESOURCE,
        OutreachAngle.TRAINING_RESOURCE, OutreachAngle.TECHNOLOGY_RESOURCE,
        OutreachAngle.FACILITY_OR_SPACE_RESOURCE, OutreachAngle.WORKFORCE_RESOURCE,
        OutreachAngle.VOLUNTEER_RESOURCE, OutreachAngle.IN_KIND_RESOURCE,
        OutreachAngle.DATA_OR_RESEARCH_RESOURCE,
    )},
    **{a: "readiness" for a in (
        OutreachAngle.READINESS_GAP, OutreachAngle.APPLICATION_READINESS,
        OutreachAngle.COMPLIANCE_READINESS, OutreachAngle.FRAGMENTED_RESEARCH,
        OutreachAngle.CATEGORY_MECHANISM, OutreachAngle.SCHOOL_SPECIFIC_RESOURCE,
    )},
}


def angle_family(angle: str) -> str:
    """The value family an angle belongs to; 'unknown' for anything unmapped."""
    return ANGLE_FAMILY.get((angle or "").strip().lower(), "unknown")


def angle_is_materially_new(previous: str, candidate: str) -> bool:
    """Is ``candidate`` a genuinely different reason to care than ``previous``?

    Same angle is never new — that is the paraphrase case this exists to catch. A
    different angle is new, and a different *family* is the strongest kind of new
    (county funding → free technical assistance rather than county → state funding).
    An unrecorded previous angle can't be compared, so anything is allowed.
    """
    prev, cand = (previous or "").strip().lower(), (candidate or "").strip().lower()
    if not prev or prev == OutreachAngle.UNCLASSIFIED:
        return True
    return prev != cand


class OutreachMessage(models.Model):
    """One outreach email — drafted, and possibly sent.

    SalesLead carries a single ``subject_line``/``outreach_draft`` pair that every
    redraft overwrites, so the system had no memory of what it had already said.
    The follow-up path worked around that by appending the old body into
    ``SalesLead.notes`` as free text — which then fed straight back into the prompt
    as a "fact about the lead", alongside the researched profile and the operator's
    own notes, all three sharing one field.

    This is that missing record. It exists so a follow-up can look up the angle the
    opener used instead of guessing from prose, and so outcomes can later be
    compared by angle, genre and structure rather than by anecdote.
    """

    class Genre(models.TextChoices):
        COLD_OPENER = "cold_opener", "Cold opener"
        COLD_FOLLOWUP = "cold_followup", "Cold follow-up"
        WARM = "warm", "Warm outreach"

    class Status(models.TextChoices):
        DRAFTED = "drafted", "Drafted"
        SENT = "sent", "Sent"
        SEND_FAILED = "send_failed", "Send failed"

    class Personalization(models.TextChoices):
        PERSONALIZED = "personalized", "Personalized"
        CATEGORY_RELEVANT = "category_relevant", "Category-relevant"

    lead = models.ForeignKey(SalesLead, on_delete=models.CASCADE, related_name="messages")
    campaign = models.ForeignKey(
        "core.Campaign", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="outreach_messages",
    )
    genre = models.CharField(max_length=20, choices=Genre.choices, default=Genre.COLD_OPENER)
    sequence_position = models.PositiveSmallIntegerField(
        default=1, help_text="1 = opener, 2 = first follow-up, and so on.")

    subject = models.CharField(max_length=300, blank=True, default="")
    body = models.TextField(blank=True, default="")

    primary_angle = models.CharField(
        max_length=40, choices=OutreachAngle.choices, blank=True, default="",
        help_text="Why the reader might care — the reason, not the source.")
    angle_detail = models.CharField(
        max_length=300, blank=True, default="",
        help_text="The concrete argument, e.g. 'CINS/FINS contract through 2026-06-30'.")
    personalization = models.CharField(
        max_length=20, choices=Personalization.choices, blank=True, default="",
        help_text="Honest classification — category-relevant is legitimate, and must not "
                  "be dressed up as research.")
    evidence_ref = models.CharField(
        max_length=200, blank=True, default="",
        help_text="Where the recipient-specific claim came from, when the research layer "
                  "exposes an identifier. Free-text until it does.")

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFTED)
    # Set only when the send actually succeeds — never on draft, queue or attempt.
    # This is the timestamp any follow-up cadence must count from.
    sent_at = models.DateTimeField(null=True, blank=True, db_index=True)
    send_error = models.TextField(blank=True, default="")
    # RFC-5322 Message-ID, so an inbound reply can be correlated back to this exact
    # message once reply ingestion exists.
    message_id = models.CharField(max_length=300, blank=True, default="")

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["lead", "-created_at"])]

    def __str__(self):
        return f"{self.lead_id} · {self.genre} · {self.primary_angle or 'unclassified'} [{self.status}]"

    @property
    def angle_family(self) -> str:
        return angle_family(self.primary_angle)

    @classmethod
    def last_for(cls, lead, *, sent_only: bool = False):
        """The most recent message for a lead, preferring what actually went out.

        ``sent_only`` matters for follow-up logic: a draft that was never sent is not
        something the recipient has seen, so it must not count as the previous touch.
        """
        qs = cls.objects.filter(lead=lead)
        if sent_only:
            qs = qs.filter(status=cls.Status.SENT)
        return qs.order_by("-sent_at", "-created_at").first()
