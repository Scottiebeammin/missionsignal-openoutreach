from django import forms

from openoutreach.signals.models import InterestSignup


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
