"""
Canonical pipeline CSV export for n8n (and any external automation).

Emits the SalesLead pipeline in the canonical n8n contract (the Schema (n8n)
tab of anansi-atlas-pipeline-MASTER.xlsx) as a live CSV, so n8n reads current
production data over HTTP instead of a stale mounted file — works on n8n Cloud
and self-hosted alike.

Auth: this is lead PII (emails), so the endpoint is gated. A request is allowed
only if it is staff (session) OR presents the shared secret in the
``X-Pipeline-Token`` header matching env ``PIPELINE_EXPORT_TOKEN``
(constant-time compare). With no token configured, only staff may export.
"""
import csv
import hashlib
import hmac
import os

from django.http import HttpResponse, HttpResponseForbidden

from openoutreach.signals.models import SalesLead

# The canonical column order the n8n composer expects.
CANON = [
    "lead_id", "dedup_key", "is_warm", "list_segment", "warmth", "campaign_track",
    "ref", "organization", "contact_name", "first_name", "last_name", "role_title",
    "email", "relationship_depth", "focus_angle", "subject_line", "stage",
    "next_action", "why_fit", "website", "email_status", "source", "date_added",
    "last_updated", "notes",
]


def _lead_id(email: str) -> str:
    return "AA-" + hashlib.sha1(email.strip().lower().encode()).hexdigest()[:10]


def saleslead_to_canonical(lead: SalesLead) -> dict:
    """Map one SalesLead onto the canonical contract dict."""
    email = (lead.email or "").strip().lower()
    name = (lead.name or "").strip()
    first, _, last = name.partition(" ")
    return {
        "lead_id": _lead_id(email) if email else "",
        "dedup_key": email,
        "is_warm": "TRUE" if lead.list_segment == "warm" else "FALSE",
        "list_segment": lead.list_segment or "",
        "warmth": lead.warmth or "",
        "campaign_track": "",
        "ref": "",
        "organization": lead.organization or "",
        "contact_name": name,
        "first_name": first,
        "last_name": last,
        "role_title": lead.role or "",
        "email": lead.email or "",
        "relationship_depth": "",
        "focus_angle": lead.focus_area or "",
        "subject_line": lead.subject_line or "",
        "stage": lead.status or "",
        "next_action": "",
        "why_fit": lead.why_fit or "",
        "website": lead.linkedin_url or "",
        "email_status": lead.email_status or "not_sent",
        "source": lead.source or "",
        "date_added": lead.created_at.date().isoformat() if lead.created_at else "",
        "last_updated": lead.updated_at.date().isoformat() if lead.updated_at else "",
        "notes": lead.notes or "",
    }


def _authorized(request) -> bool:
    if request.user.is_authenticated and request.user.is_staff:
        return True
    expected = os.getenv("PIPELINE_EXPORT_TOKEN", "")
    presented = request.headers.get("X-Pipeline-Token", "")
    return bool(expected) and hmac.compare_digest(expected, presented)


def pipeline_csv_export(request):
    """GET the canonical pipeline as text/csv. Token- or staff-gated (PII)."""
    if not _authorized(request):
        return HttpResponseForbidden("Missing or invalid X-Pipeline-Token.")
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="anansi-atlas-pipeline-system.csv"'
    writer = csv.DictWriter(response, fieldnames=CANON)
    writer.writeheader()
    for lead in SalesLead.objects.all().order_by("-updated_at"):
        writer.writerow(saleslead_to_canonical(lead))
    return response
