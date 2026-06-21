from django import forms

from openoutreach.signals.models import InterestSignup, PilotFeedback, PilotProfile


def _split_lines(value: str) -> list[str]:
    return [line.strip() for line in value.splitlines() if line.strip()]


class OrganizationIntakeForm(forms.Form):
    BUDGET_RANGE_CHOICES = [
        ("", "Not provided"),
        ("Under $250K", "Under $250K"),
        ("$250K - $1M", "$250K - $1M"),
        ("$1M - $5M", "$1M - $5M"),
        ("$5M+", "$5M+"),
    ]

    organization_name = forms.CharField(label="Organization Name", max_length=255)
    website = forms.URLField(label="Website", max_length=500)
    mission = forms.CharField(
        label="Mission Statement",
        widget=forms.Textarea(attrs={"rows": 5}),
    )
    programs = forms.CharField(
        label="Programs",
        widget=forms.Textarea(attrs={"rows": 8}),
    )
    organization_type = forms.CharField(
        label="Organization Type (optional)",
        max_length=255,
        required=False,
        help_text="Examples: nonprofit, fiscally sponsored project, school, coalition.",
    )
    city = forms.CharField(label="City (optional)", max_length=255, required=False)
    county = forms.CharField(label="County (optional)", max_length=255, required=False)
    state = forms.CharField(label="State (optional)", max_length=255, required=False)
    service_area_notes = forms.CharField(
        label="Service Area Notes (optional)",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    outcomes_and_impact = forms.CharField(
        label="Outcomes / Impact (optional)",
        required=False,
        help_text="Use one outcome per line.",
        widget=forms.Textarea(attrs={"rows": 4}),
    )
    budget_range = forms.ChoiceField(
        label="Budget Range (optional)",
        choices=BUDGET_RANGE_CHOICES,
        required=False,
    )
    current_funding_sources = forms.CharField(
        label="Current Funding Sources (optional)",
        required=False,
        help_text="Use one source per line.",
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    existing_partnerships = forms.CharField(
        label="Existing Partnerships (optional)",
        required=False,
        help_text="Use one partnership per line.",
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def clean_outcomes_and_impact(self):
        return _split_lines(self.cleaned_data["outcomes_and_impact"])

    def clean_current_funding_sources(self):
        return _split_lines(self.cleaned_data["current_funding_sources"])

    def clean_existing_partnerships(self):
        return _split_lines(self.cleaned_data["existing_partnerships"])


class InterestSignupForm(forms.ModelForm):
    class Meta:
        model = InterestSignup
        fields = [
            "name",
            "organization",
            "email",
            "role",
            "website",
            "interest_type",
            "message",
        ]
        widgets = {
            "message": forms.Textarea(attrs={"rows": 4}),
        }


class PilotDiscoveryQuestionnaireForm(forms.ModelForm):
    class Meta:
        model = PilotProfile
        fields = [
            "organization_name",
            "website",
            "mission",
            "location",
            "year_founded",
            "annual_budget_range",
            "team_size",
            "primary_programs",
            "communities_served",
            "current_initiatives",
            "geographic_reach",
            "current_revenue_sources",
            "grant_experience",
            "major_funders",
            "fundraising_activities",
            "funding_challenges",
            "key_partners",
            "community_relationships",
            "strategic_relationships",
            "government_relationships",
            "corporate_relationships",
            "top_goals",
            "biggest_challenges",
            "desired_outcomes",
            "success_definition",
            "strategic_plan",
            "annual_report",
            "grant_materials",
            "program_information",
            "other_documents",
            "document_notes",
        ]
        widgets = {
            "mission": forms.Textarea(attrs={"rows": 4}),
            "primary_programs": forms.Textarea(attrs={"rows": 4}),
            "communities_served": forms.Textarea(attrs={"rows": 3}),
            "current_initiatives": forms.Textarea(attrs={"rows": 3}),
            "geographic_reach": forms.Textarea(attrs={"rows": 3}),
            "current_revenue_sources": forms.Textarea(attrs={"rows": 3}),
            "grant_experience": forms.Textarea(attrs={"rows": 3}),
            "major_funders": forms.Textarea(attrs={"rows": 3}),
            "fundraising_activities": forms.Textarea(attrs={"rows": 3}),
            "funding_challenges": forms.Textarea(attrs={"rows": 3}),
            "key_partners": forms.Textarea(attrs={"rows": 3}),
            "community_relationships": forms.Textarea(attrs={"rows": 3}),
            "strategic_relationships": forms.Textarea(attrs={"rows": 3}),
            "government_relationships": forms.Textarea(attrs={"rows": 3}),
            "corporate_relationships": forms.Textarea(attrs={"rows": 3}),
            "top_goals": forms.Textarea(attrs={"rows": 3}),
            "biggest_challenges": forms.Textarea(attrs={"rows": 3}),
            "desired_outcomes": forms.Textarea(attrs={"rows": 3}),
            "success_definition": forms.Textarea(attrs={"rows": 3}),
            "document_notes": forms.Textarea(attrs={"rows": 3}),
        }


class PilotFeedbackForm(forms.ModelForm):
    class Meta:
        model = PilotFeedback
        fields = [
            "most_valuable",
            "confusing",
            "indispensable",
            "would_recommend",
            "additional_feedback",
        ]
        widgets = {
            "most_valuable": forms.Textarea(attrs={"rows": 4}),
            "confusing": forms.Textarea(attrs={"rows": 4}),
            "indispensable": forms.Textarea(attrs={"rows": 4}),
            "additional_feedback": forms.Textarea(attrs={"rows": 4}),
        }
