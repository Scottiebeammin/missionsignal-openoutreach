# openoutreach/crm/admin.py
from django.contrib import admin
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe

from openoutreach.crm.models import Lead


class HasIntelFilter(admin.SimpleListFilter):
    """Filter on the company_intel tri-state (null / {} / data)."""

    title = "company intel"
    parameter_name = "intel"

    def lookups(self, request, model_admin):
        return [
            ("yes", "Has intel"),
            ("empty", "Tried — site yielded nothing"),
            ("no", "Not resolved"),
        ]

    def queryset(self, request, queryset):
        # NB: JSONField `=None` means JSON null, not SQL NULL — use __isnull.
        if self.value() == "yes":
            return queryset.filter(company_intel__isnull=False).exclude(company_intel={})
        if self.value() == "empty":
            return queryset.filter(company_intel={})
        if self.value() == "no":
            return queryset.filter(company_intel__isnull=True)
        return queryset


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = (
        "public_identifier", "api_email", "intel_company", "intel_industry",
        "disqualified", "creation_date",
    )
    list_filter = (HasIntelFilter, "disqualified")
    search_fields = ("public_identifier", "linkedin_url", "api_email")
    ordering = ("-creation_date",)
    # embedding is raw float32 bytes — useless (and heavy) in a form.
    exclude = ("embedding",)
    readonly_fields = ("company_intel_panel", "creation_date", "update_date")

    # ── list columns ──

    @admin.display(description="Company")
    def intel_company(self, obj):
        intel = obj.company_intel or {}
        return intel.get("company_name") or "—"

    @admin.display(description="Industry")
    def intel_industry(self, obj):
        intel = obj.company_intel or {}
        return ", ".join(intel.get("industry_signals") or []) or "—"

    # ── detail panel ──

    @admin.display(description="Company intel (rendered)")
    def company_intel_panel(self, obj):
        """Human-readable rendering of the scraped firmographics.

        The raw JSON stays editable in the ``company_intel`` field below it
        (clear it to null to force a re-scrape on the next enrichment pass).
        All values are scraped from external sites — format_html escapes them.
        """
        intel = obj.company_intel
        if intel is None:
            return "Not resolved yet — no company domain seen for this lead."
        if not intel:
            return "Tried — the company site yielded nothing."

        rows = []

        def row(label, value):
            if value:
                rows.append(format_html(
                    '<tr><th style="text-align:left;vertical-align:top;'
                    'padding:2px 12px 2px 0">{}</th><td>{}</td></tr>',
                    label, value,
                ))

        size = intel.get("company_size_signals") or {}
        contact = intel.get("contact_info") or {}
        team = intel.get("team_members") or []

        row("Company", intel.get("company_name"))
        row("Domain", intel.get("domain"))
        row("Description", intel.get("description"))
        row("Industry", ", ".join(intel.get("industry_signals") or []))
        row("Tech stack", ", ".join(intel.get("tech_stack") or []))
        row("Employees", size.get("estimated_employees"))
        row("Funding", size.get("funding_stage"))
        row("Hiring", "yes" if intel.get("has_job_postings") else "")
        if intel.get("social_links"):
            links = format_html_join(
                " · ", '<a href="{}" target="_blank" rel="noopener">{}</a>',
                ((urls[0], platform) for platform, urls in intel["social_links"].items() if urls),
            )
            row("Socials", links)
        if team:
            people = format_html_join(
                mark_safe("<br>"), "{} — {}",
                ((m.get("name", ""), m.get("title", "") or "?") for m in team[:10]),
            )
            row("Team", people)
        row("Emails", ", ".join(contact.get("emails") or []))
        row("Phones", ", ".join(contact.get("phones") or []))
        row("Pages analyzed", str(len(intel.get("pages_analyzed") or [])))

        return format_html("<table>{}</table>", mark_safe("".join(rows)))
