from django import forms

from openoutreach.signals.categories import OPPORTUNITY_FOCUS_CATEGORIES
from openoutreach.signals.models import InterestSignup, PilotFeedback, PilotProfile


def _split_lines(value: str) -> list[str]:
    return [line.strip() for line in value.splitlines() if line.strip()]


BENEFICIARY_CHOICES = [
    ("youth", "Youth & Young People"),
    ("girls and young women", "Girls & Young Women"),
    ("families", "Families"),
    ("seniors", "Seniors & Older Adults"),
    ("veterans", "Veterans"),
    ("job seekers", "Job Seekers & Workforce"),
    ("small businesses", "Small Businesses & Entrepreneurs"),
    ("people experiencing homelessness", "People Experiencing Homelessness"),
    ("immigrants and refugees", "Immigrants & Refugees"),
    ("people with disabilities", "People with Disabilities"),
    ("LGBTQ+ individuals", "LGBTQ+ Individuals"),
    ("justice-involved individuals", "Justice-Involved Individuals"),
    ("low-income residents", "Low-Income Residents"),
    ("communities of color", "Communities of Color"),
    ("rural residents", "Rural Residents"),
    ("communities", "General Community / Residents"),
]


class OrganizationIntakeForm(forms.Form):
    BUDGET_RANGE_CHOICES = [
        ("", "Not provided"),
        ("Under $250K", "Under $250K"),
        ("$250K - $1M", "$250K - $1M"),
        ("$1M - $5M", "$1M - $5M"),
        ("$5M+", "$5M+"),
    ]

    contact_name = forms.CharField(label="Your Full Name", max_length=255)
    contact_position = forms.CharField(label="Position / Title", max_length=255)
    contact_email = forms.EmailField(label="Work Email")

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
    city = forms.CharField(label="City", max_length=255)
    county = forms.CharField(label="County (optional)", max_length=255, required=False)
    state = forms.CharField(label="State", max_length=255)
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

    focus_area_selections = forms.MultipleChoiceField(
        label="Focus Areas",
        choices=[(c, c) for c in OPPORTUNITY_FOCUS_CATEGORIES],
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text="Select all that apply — this directly shapes which funders and partners appear in your Opportunity Web.",
    )
    beneficiary_selections = forms.MultipleChoiceField(
        label="Who does your organization serve?",
        choices=BENEFICIARY_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text="Select all populations your programs primarily serve.",
    )
    intake_notes = forms.CharField(
        label="How can Anansi Atlas help?",
        required=False,
        widget=forms.Textarea(attrs={"rows": 5}),
        help_text="Share the specific challenges, goals, or areas where you're looking for support. This helps us tailor your Opportunity Web to what matters most.",
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
            "primary_programs",
            "communities_served",
            "current_initiatives",
            "current_revenue_sources",
            "grant_experience",
            "major_funders",
            "key_partners",
            "strategic_relationships",
            "top_goals",
            "biggest_challenges",
            "desired_outcomes",
            "strategic_plan",
            "annual_report",
            "grant_materials",
            "program_information",
            "other_documents",
            "document_notes",
        ]
        labels = {
            "location": "Geography",
            "primary_programs": "Programs",
            "communities_served": "Communities Served",
            "current_initiatives": "Current Priorities",
            "current_revenue_sources": "Funding Sources",
            "grant_experience": "Grant Experience",
            "major_funders": "Major Funders",
            "key_partners": "Key Partners",
            "strategic_relationships": "Strategic Relationships",
            "top_goals": "Top 3 Goals",
            "biggest_challenges": "Biggest Challenges",
            "desired_outcomes": "Desired Outcomes",
        }
        widgets = {
            "mission": forms.Textarea(attrs={"rows": 4}),
            "primary_programs": forms.Textarea(attrs={"rows": 4}),
            "communities_served": forms.Textarea(attrs={"rows": 3}),
            "current_initiatives": forms.Textarea(attrs={"rows": 3}),
            "current_revenue_sources": forms.Textarea(attrs={"rows": 3}),
            "grant_experience": forms.Textarea(attrs={"rows": 3}),
            "major_funders": forms.Textarea(attrs={"rows": 3}),
            "key_partners": forms.Textarea(attrs={"rows": 3}),
            "strategic_relationships": forms.Textarea(attrs={"rows": 3}),
            "top_goals": forms.Textarea(attrs={"rows": 3}),
            "biggest_challenges": forms.Textarea(attrs={"rows": 3}),
            "desired_outcomes": forms.Textarea(attrs={"rows": 3}),
            "document_notes": forms.Textarea(attrs={"rows": 3}),
        }


class PilotFeedbackForm(forms.ModelForm):
    most_valuable = forms.CharField(
        label="What was most valuable?",
        widget=forms.Textarea(attrs={"rows": 4}),
    )
    confusing = forms.CharField(
        label="What was confusing?",
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
    )
    indispensable = forms.CharField(
        label="What would make Anansi Atlas indispensable?",
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
    )
    would_recommend = forms.ChoiceField(
        label="Would you recommend Anansi Atlas?",
        choices=PilotFeedback.Recommendation.choices,
    )
    additional_feedback = forms.CharField(
        label="Additional comments",
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
    )

    class Meta:
        model = PilotFeedback
        fields = [
            "most_valuable",
            "confusing",
            "indispensable",
            "would_recommend",
            "additional_feedback",
        ]
