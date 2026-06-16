from django import forms

class OrganizationIntakeForm(forms.Form):
    organization_name = forms.CharField(max_length=255)
    website = forms.URLField(max_length=500)
    mission = forms.CharField(widget=forms.Textarea(attrs={"rows": 5}))
    programs = forms.CharField(widget=forms.Textarea(attrs={"rows": 8}))
