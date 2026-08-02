from django.contrib import admin

from openoutreach.grants.models import (
    GrantAnswerLibraryItem,
    GrantApplication,
    GrantApplicationSection,
)


class GrantApplicationSectionInline(admin.TabularInline):
    model = GrantApplicationSection
    extra = 0
    fields = ("order", "title", "status", "word_limit", "character_limit", "last_generated_at")
    readonly_fields = ("last_generated_at",)
    ordering = ("order",)
    show_change_link = True


@admin.register(GrantApplication)
class GrantApplicationAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "funder_name", "status", "deadline", "updated_at")
    list_filter = ("status", "deadline")
    search_fields = ("title", "funder_name", "project__name", "project__organization__name")
    autocomplete_fields = ()
    raw_id_fields = ("project", "opportunity", "funding_signal", "created_by")
    inlines = (GrantApplicationSectionInline,)
    readonly_fields = ("created_at", "updated_at")


@admin.register(GrantApplicationSection)
class GrantApplicationSectionAdmin(admin.ModelAdmin):
    list_display = ("title", "application", "status", "required", "updated_at")
    list_filter = ("status", "required", "section_key")
    search_fields = ("title", "application__title", "draft_response", "approved_response")
    raw_id_fields = ("application", "approved_by")
    readonly_fields = ("last_generated_at", "approved_at", "created_at", "updated_at")


@admin.register(GrantAnswerLibraryItem)
class GrantAnswerLibraryItemAdmin(admin.ModelAdmin):
    list_display = ("title", "organization", "category", "approval_status", "updated_at")
    list_filter = ("category", "approval_status")
    search_fields = ("title", "answer", "organization__name")
    raw_id_fields = (
        "organization", "project", "source_application", "source_section",
        "created_by", "updated_by",
    )
    readonly_fields = ("created_at", "updated_at")
