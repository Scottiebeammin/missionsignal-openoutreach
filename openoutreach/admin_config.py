"""Curated Django admin for Anansi Atlas operators.

The project is built on a LinkedIn-automation base (OpenOutreach), so the raw
admin lists ~37 models — most of which an Anansi Atlas operator never touches.
This AdminConfig runs after autodiscover registers everything, then unregisters
the base-platform noise and internal plumbing, leaving a digestible control
panel: clients, waitlist, the Opportunity Web data (funders/partners/resources/
opportunities), analysis runs, and config.

Wired in via INSTALLED_APPS ("openoutreach.admin_config.AnansiAdminConfig"
replaces "django.contrib.admin").
"""

from django.contrib.admin.apps import AdminConfig


class AnansiAdminConfig(AdminConfig):
    def ready(self):
        super().ready()  # autodiscover all app admin.py registrations first

        from django.contrib import admin
        from django.contrib.admin.sites import NotRegistered

        admin.site.site_header = "Anansi Atlas — Admin"
        admin.site.site_title = "Anansi Atlas Admin"
        admin.site.index_title = "Operations"

        from openoutreach.chat.models import ChatMessage
        from openoutreach.core.models import Campaign, Task
        from openoutreach.funding.models import (
            DocumentVaultItem,
            EvidenceLibraryItem,
            FundingOpportunity,
            FundingOpportunitySource,
            FundingSignal,
            FundingSignalFeedback,
            OpportunityDeadline,
            OpportunityDocumentRequirement,
            OpportunityTask,
            SourceOrganization,
        )
        from openoutreach.linkedin.models import ActionLog, LinkedInProfile, SearchKeyword
        from openoutreach.signals.models import (
            Celebration,
            OrganizationContact,
            OrganizationSourcePage,
            PartnerOrganization as RelationshipPartnerOrganization,
            PilotFeedback,
        )
        from openoutreach.sources.models import SearchQuery, Source, SourceRecord

        from django.contrib.auth.models import Group
        from django.contrib.sites.models import Site

        hidden = [
            # Django built-ins a solo operator doesn't manage
            Group, Site,
            # LinkedIn-automation base — unused by Anansi Atlas
            LinkedInProfile, SearchKeyword, ActionLog, ChatMessage,
            Source, SearchQuery, SourceRecord, Campaign, Task,
            # Internal funding plumbing / signal pipeline
            SourceOrganization, OpportunityTask, OpportunityDeadline,
            DocumentVaultItem, EvidenceLibraryItem, OpportunityDocumentRequirement,
            FundingOpportunity, FundingOpportunitySource, FundingSignal, FundingSignalFeedback,
            # Secondary signals models (kept out of the day-to-day view)
            Celebration, OrganizationContact, OrganizationSourcePage, PilotFeedback,
            RelationshipPartnerOrganization,
        ]

        for model in hidden:
            try:
                admin.site.unregister(model)
            except NotRegistered:
                pass
