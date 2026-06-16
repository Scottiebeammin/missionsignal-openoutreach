# openoutreach/core/admin.py
from django.contrib import admin
from django.contrib import messages

from openoutreach.core.models import Campaign, Organization, Project, SiteConfig, Task
from openoutreach.signals.analysis_service import analyze_project


@admin.register(SiteConfig)
class SiteConfigAdmin(admin.ModelAdmin):
    list_display = ("__str__", "llm_provider", "ai_model", "llm_api_base")

    def has_add_permission(self, request):
        return not SiteConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ("name", "booking_link", "is_freemium", "action_fraction")
    filter_horizontal = ("users",)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "website", "city", "state", "analysis_status", "active", "created_at")
    list_filter = ("analysis_status", "active", "state")
    search_fields = ("name", "website", "mission", "city", "county", "state", "service_area_notes")
    filter_horizontal = ("users",)
    readonly_fields = (
        "analysis_status", "analysis_confidence", "analysis_warnings",
        "analyzer_version", "last_analyzed_at", "created_at", "updated_at",
    )


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "active", "created_at")
    list_filter = ("active",)
    search_fields = ("name", "organization__name", "organization__website", "programs")
    raw_id_fields = ("organization",)
    filter_horizontal = ("users",)
    readonly_fields = ("created_at", "updated_at")
    actions = ("run_deterministic_analysis",)

    @admin.action(description="Run deterministic organization analysis")
    def run_deterministic_analysis(self, request, queryset):
        analyzed = 0
        for project in queryset.select_related("organization"):
            analyze_project(project, mode="deterministic")
            analyzed += 1
        self.message_user(
            request,
            f"Analyzed {analyzed} project(s).",
            level=messages.SUCCESS,
        )


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("task_type", "status", "scheduled_at", "payload", "created_at")
    list_filter = ("task_type", "status")
    readonly_fields = (
        "task_type", "status", "scheduled_at", "payload",
        "created_at", "started_at", "completed_at",
    )
    date_hierarchy = "scheduled_at"
