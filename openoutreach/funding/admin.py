from django.contrib import admin

from openoutreach.funding.models import (
    Funder,
    DocumentVaultItem,
    EvidenceLibraryItem,
    FundingCriteria,
    FundingOpportunity,
    FundingOpportunitySource,
    FundingSignal,
    FundingSignalFeedback,
    GovernmentEntity,
    Opportunity,
    OpportunityDeadline,
    OpportunityDocumentRequirement,
    OpportunityTask,
    PartnerOrganization,
    ResourceProvider,
    SourceOrganization,
)


@admin.register(FundingCriteria)
class FundingCriteriaAdmin(admin.ModelAdmin):
    list_display = ("project", "deadline_horizon_days", "analyzer_confidence", "updated_at")
    search_fields = ("project__organization__name", "inclusion_criteria", "exclusion_criteria")
    raw_id_fields = ("project", "source_analysis_run")


@admin.register(Funder)
class FunderAdmin(admin.ModelAdmin):
    list_display = ("name", "funder_type", "geography", "active", "website")
    list_filter = ("funder_type", "active")
    search_fields = ("name", "eligibility_notes", "notes", "website")


@admin.register(GovernmentEntity)
class GovernmentEntityAdmin(admin.ModelAdmin):
    list_display = ("name", "entity_type", "department_or_office", "geography", "active", "website")
    list_filter = ("entity_type", "active")
    search_fields = ("name", "department_or_office", "notes", "website")


@admin.register(ResourceProvider)
class ResourceProviderAdmin(admin.ModelAdmin):
    list_display = ("name", "resource_type", "geography", "active", "website")
    list_filter = ("resource_type", "active")
    search_fields = ("name", "eligibility_notes", "notes", "website")


@admin.register(PartnerOrganization)
class PartnerOrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "partner_type", "geography", "active", "website")
    list_filter = ("partner_type", "active")
    search_fields = ("name", "notes", "website")


@admin.register(SourceOrganization)
class SourceOrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "organization_type", "geography", "active", "website")
    list_filter = ("organization_type", "active")
    search_fields = ("name", "notes", "website")


@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = (
        "name", "opportunity_type", "source_organization", "source_type",
        "status", "lifecycle_status", "priority_level", "assigned_owner", "deadline",
    )
    list_filter = (
        "opportunity_type", "source_type", "status", "lifecycle_status",
        "priority_level", "source_organization", "assigned_owner",
    )
    search_fields = ("name", "source_name", "source_organization__name", "eligibility_notes", "notes")
    raw_id_fields = ("source_organization", "assigned_owner")
    date_hierarchy = "deadline"


@admin.register(OpportunityTask)
class OpportunityTaskAdmin(admin.ModelAdmin):
    list_display = ("title", "opportunity", "status", "priority", "due_date", "owner", "updated_at")
    list_filter = ("status", "priority", "owner")
    search_fields = ("title", "description", "opportunity__name", "owner__username")
    raw_id_fields = ("opportunity", "owner")
    date_hierarchy = "due_date"


@admin.register(OpportunityDeadline)
class OpportunityDeadlineAdmin(admin.ModelAdmin):
    list_display = ("title", "opportunity", "deadline_type", "status", "deadline_date", "updated_at")
    list_filter = ("deadline_type", "status")
    search_fields = ("title", "notes", "opportunity__name")
    raw_id_fields = ("opportunity",)
    date_hierarchy = "deadline_date"


@admin.register(DocumentVaultItem)
class DocumentVaultItemAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "document_type", "status", "uploaded_at", "updated_at")
    list_filter = ("document_type", "status")
    search_fields = ("title", "notes", "project__organization__name", "project__name", "file_reference")
    raw_id_fields = ("project",)
    date_hierarchy = "updated_at"


@admin.register(EvidenceLibraryItem)
class EvidenceLibraryItemAdmin(admin.ModelAdmin):
    list_display = (
        "title", "project", "evidence_type", "related_program", "metric_name", "status", "evidence_date",
    )
    list_filter = ("evidence_type", "status")
    search_fields = (
        "title", "notes", "related_program", "metric_name", "metric_value",
        "project__organization__name", "project__name",
    )
    raw_id_fields = ("project",)
    date_hierarchy = "evidence_date"


@admin.register(OpportunityDocumentRequirement)
class OpportunityDocumentRequirementAdmin(admin.ModelAdmin):
    list_display = ("title", "opportunity", "requirement_type", "status", "linked_document", "updated_at")
    list_filter = ("requirement_type", "status")
    search_fields = ("title", "notes", "opportunity__name", "linked_document__title")
    raw_id_fields = ("opportunity", "linked_document")
    date_hierarchy = "updated_at"


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
