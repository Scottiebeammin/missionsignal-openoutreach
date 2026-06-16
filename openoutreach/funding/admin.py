from django.contrib import admin

from openoutreach.funding.models import (
    Funder,
    FundingCriteria,
    FundingOpportunity,
    FundingOpportunitySource,
    FundingSignal,
    FundingSignalFeedback,
)


@admin.register(FundingCriteria)
class FundingCriteriaAdmin(admin.ModelAdmin):
    list_display = ("project", "deadline_horizon_days", "analyzer_confidence", "updated_at")
    search_fields = ("project__organization__name", "inclusion_criteria", "exclusion_criteria")
    raw_id_fields = ("project", "source_analysis_run")


@admin.register(Funder)
class FunderAdmin(admin.ModelAdmin):
    list_display = ("name", "funder_type", "website")
    list_filter = ("funder_type",)
    search_fields = ("name", "description")


class FundingOpportunitySourceInline(admin.TabularInline):
    model = FundingOpportunitySource
    extra = 0
    raw_id_fields = ("source_record",)
    readonly_fields = ("source_external_id", "source_url", "first_seen_at", "last_seen_at")


@admin.register(FundingOpportunity)
class FundingOpportunityAdmin(admin.ModelAdmin):
    list_display = ("title", "funder", "status", "deadline_at", "amount_min", "amount_max")
    list_filter = ("status", "opportunity_type")
    search_fields = ("title", "summary", "external_id")
    raw_id_fields = ("funder",)
    readonly_fields = ("identity_key",)
    inlines = (FundingOpportunitySourceInline,)
    date_hierarchy = "deadline_at"


@admin.register(FundingOpportunitySource)
class FundingOpportunitySourceAdmin(admin.ModelAdmin):
    list_display = ("opportunity", "source_record", "is_primary", "first_seen_at", "last_seen_at")
    search_fields = ("opportunity__title", "source_external_id", "source_url")
    raw_id_fields = ("opportunity", "source_record")


@admin.register(FundingSignal)
class FundingSignalAdmin(admin.ModelAdmin):
    list_display = ("project", "opportunity", "state", "score", "confidence", "eligibility_status")
    list_filter = ("state", "eligibility_status")
    search_fields = ("project__organization__name", "opportunity__title", "explanation")
    raw_id_fields = ("project", "opportunity", "owner")


@admin.register(FundingSignalFeedback)
class FundingSignalFeedbackAdmin(admin.ModelAdmin):
    list_display = ("signal", "label", "user", "created_at")
    list_filter = ("label",)
    search_fields = ("reason", "signal__opportunity__title")
    raw_id_fields = ("signal", "user")
