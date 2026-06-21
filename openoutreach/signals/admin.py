from django.contrib import admin
from django.db.models import Q

from openoutreach.signals.models import (
    Celebration,
    InterestSignup,
    OrganizationAnalysisRun,
    OrganizationContact,
    OrganizationSourcePage,
    PartnerOrganization,
    PilotFeedback,
    PilotProfile,
)


class PilotOperationalFilter(admin.SimpleListFilter):
    title = "Pilot command center"
    parameter_name = "pilot_command"

    def lookups(self, request, model_admin):
        return (
            ("active", "Active Pilots"),
            ("snapshot_needed", "Snapshot Needed"),
            ("walkthrough_needed", "Walkthrough Needed"),
            ("feedback_missing", "Feedback Missing"),
            ("completed", "Completed"),
        )

    def queryset(self, request, queryset):
        if self.value() == "active":
            return queryset.exclude(
                lifecycle_status__in=[
                    PilotProfile.LifecycleStatus.WAITLIST,
                    PilotProfile.LifecycleStatus.PILOT_COMPLETE,
                ]
            )
        if self.value() == "snapshot_needed":
            return queryset.exclude(snapshot_status=PilotProfile.SnapshotStatus.DELIVERED)
        if self.value() == "walkthrough_needed":
            return queryset.filter(
                lifecycle_status__in=[
                    PilotProfile.LifecycleStatus.SNAPSHOT_DELIVERED,
                    PilotProfile.LifecycleStatus.WALKTHROUGH_SCHEDULED,
                    PilotProfile.LifecycleStatus.ACTIVE_PILOT,
                ],
            ).exclude(walkthrough_status=PilotProfile.WalkthroughStatus.COMPLETED)
        if self.value() == "feedback_missing":
            return queryset.filter(
                Q(lifecycle_status=PilotProfile.LifecycleStatus.ACTIVE_PILOT)
                | Q(lifecycle_status=PilotProfile.LifecycleStatus.SNAPSHOT_DELIVERED)
                | Q(walkthrough_status=PilotProfile.WalkthroughStatus.COMPLETED),
                feedback__isnull=True,
            )
        if self.value() == "completed":
            return queryset.filter(lifecycle_status=PilotProfile.LifecycleStatus.PILOT_COMPLETE)
        return queryset


@admin.register(Celebration)
class CelebrationAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "celebration_type", "organization_name", "updated_at")
    list_filter = ("celebration_type",)
    search_fields = ("title", "description", "impact", "organization_name", "project__name")
    raw_id_fields = ("project",)
    date_hierarchy = "created_at"


@admin.register(OrganizationContact)
class OrganizationContactAdmin(admin.ModelAdmin):
    list_display = ("name", "project", "organization", "contact_type", "relationship_strength", "status", "updated_at")
    list_filter = ("contact_type", "relationship_strength", "status")
    search_fields = ("name", "title", "organization", "email", "notes", "project__name")
    raw_id_fields = ("project",)
    date_hierarchy = "updated_at"


@admin.register(PartnerOrganization)
class RelationshipPartnerOrganizationAdmin(admin.ModelAdmin):
    list_display = ("organization_name", "project", "partner_type", "relationship_strength", "status", "website")
    list_filter = ("partner_type", "relationship_strength", "status")
    search_fields = ("organization_name", "notes", "website", "project__name")
    raw_id_fields = ("project",)
    date_hierarchy = "updated_at"


@admin.register(InterestSignup)
class InterestSignupAdmin(admin.ModelAdmin):
    list_display = ("organization", "name", "email", "interest_type", "status", "created_at")
    list_filter = ("interest_type", "status", "created_at")
    search_fields = ("name", "organization", "email", "role", "website", "message")
    date_hierarchy = "created_at"


@admin.register(PilotProfile)
class PilotProfileAdmin(admin.ModelAdmin):
    list_display = (
        "organization_name",
        "contact_name",
        "email",
        "lifecycle_status",
        "snapshot_status",
        "snapshot_link",
        "walkthrough_status",
        "assigned_reviewer",
        "updated_at",
    )
    list_editable = ("lifecycle_status",)
    list_filter = (
        PilotOperationalFilter,
        "lifecycle_status",
        "snapshot_status",
        "walkthrough_status",
        "created_at",
        "updated_at",
    )
    search_fields = (
        "organization_name",
        "contact_name",
        "email",
        "website",
        "mission",
        "assigned_reviewer",
        "snapshot_link",
        "snapshot_notes",
        "internal_comments",
    )
    raw_id_fields = ("signup", "project")
    date_hierarchy = "updated_at"
    fieldsets = (
        ("Pilot Lifecycle", {"fields": ("signup", "project", "lifecycle_status")}),
        ("Organization", {"fields": ("organization_name", "contact_name", "email", "website", "mission", "location", "year_founded", "annual_budget_range", "team_size")}),
        ("Programs", {"fields": ("primary_programs", "communities_served", "current_initiatives", "geographic_reach")}),
        ("Funding", {"fields": ("current_revenue_sources", "grant_experience", "major_funders", "fundraising_activities", "funding_challenges")}),
        ("Partnerships", {"fields": ("key_partners", "community_relationships", "strategic_relationships", "government_relationships", "corporate_relationships")}),
        ("Growth Goals", {"fields": ("top_goals", "biggest_challenges", "desired_outcomes", "success_definition")}),
        ("Documents", {"fields": ("strategic_plan", "annual_report", "grant_materials", "program_information", "other_documents", "document_notes")}),
        ("Snapshot Workflow", {"fields": ("snapshot_status", "assigned_reviewer", "snapshot_notes", "snapshot_link", "snapshot_delivery_date", "internal_comments")}),
        ("Founder Walkthrough", {"fields": ("walkthrough_status", "meeting_date", "meeting_notes", "follow_up_actions", "recommended_next_steps", "action_plan_started")}),
    )


@admin.register(PilotFeedback)
class PilotFeedbackAdmin(admin.ModelAdmin):
    list_display = ("pilot", "would_recommend", "created_at", "updated_at")
    list_filter = ("would_recommend", "created_at")
    search_fields = (
        "pilot__organization_name",
        "most_valuable",
        "confusing",
        "indispensable",
        "additional_feedback",
    )
    raw_id_fields = ("pilot",)
    date_hierarchy = "created_at"


@admin.register(OrganizationSourcePage)
class OrganizationSourcePageAdmin(admin.ModelAdmin):
    list_display = (
        "organization", "project", "title", "source_type", "review_status", "relevance",
        "fetch_status", "last_reviewed_at", "updated_at",
    )
    list_filter = ("source_type", "review_status", "relevance", "fetch_status", "page_type")
    list_editable = ("review_status", "relevance")
    search_fields = (
        "organization__name", "project__name", "title", "url", "raw_text", "notes",
    )
    raw_id_fields = ("organization", "project")
    date_hierarchy = "last_reviewed_at"


@admin.register(OrganizationAnalysisRun)
class OrganizationAnalysisRunAdmin(admin.ModelAdmin):
    list_display = ("organization", "status", "analyzer_version", "created_at", "completed_at")
    list_filter = ("status", "analyzer_version")
    raw_id_fields = ("organization",)
    readonly_fields = ("input_snapshot", "output_snapshot", "warnings", "error", "created_at")
