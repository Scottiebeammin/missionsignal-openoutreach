from django.contrib import admin

from openoutreach.signals.models import (
    Celebration,
    InterestSignup,
    OrganizationAnalysisRun,
    OrganizationContact,
    OrganizationSourcePage,
    PartnerOrganization,
)


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
