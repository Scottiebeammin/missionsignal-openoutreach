from django.contrib import admin

from openoutreach.sources.models import SearchQuery, Source, SourceRecord


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ("name", "key", "source_type", "active")
    list_filter = ("source_type", "active")
    search_fields = ("name", "key")


@admin.register(SearchQuery)
class SearchQueryAdmin(admin.ModelAdmin):
    list_display = ("query", "project", "source", "signal_type", "status", "priority", "result_count")
    list_filter = ("signal_type", "status", "source")
    search_fields = ("query", "rationale")
    raw_id_fields = ("project", "source")
    readonly_fields = ("filters_hash",)


@admin.register(SourceRecord)
class SourceRecordAdmin(admin.ModelAdmin):
    list_display = ("title", "source", "external_id", "processing_status", "last_seen_at")
    list_filter = ("source", "processing_status")
    search_fields = ("title", "external_id", "canonical_url", "raw_text")
    filter_horizontal = ("search_queries",)
