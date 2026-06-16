from django.contrib import admin

from openoutreach.signals.models import OrganizationAnalysisRun, OrganizationSourcePage


@admin.register(OrganizationSourcePage)
class OrganizationSourcePageAdmin(admin.ModelAdmin):
    list_display = ("organization", "title", "page_type", "fetch_status", "fetched_at")
    list_filter = ("fetch_status", "page_type")
    search_fields = ("title", "url", "raw_text")
    raw_id_fields = ("organization",)


@admin.register(OrganizationAnalysisRun)
class OrganizationAnalysisRunAdmin(admin.ModelAdmin):
    list_display = ("organization", "status", "analyzer_version", "created_at", "completed_at")
    list_filter = ("status", "analyzer_version")
    raw_id_fields = ("organization",)
    readonly_fields = ("input_snapshot", "output_snapshot", "warnings", "error", "created_at")
