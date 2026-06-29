"""
Render branded HTML email templates for Anansi Atlas.
"""
from django.template.loader import render_to_string


def render_email(template_name: str, context: dict) -> str:
    return render_to_string(f"signals/emails/{template_name}", context)
