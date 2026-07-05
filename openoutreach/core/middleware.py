"""Portal middleware: view-as-client banner + client activity tracking.

ViewAsClientBanner — when a staff operator opens a client's project portal (any
`project-*` route) for a project they don't personally belong to, inject a sticky
banner so the "view as client" mode is unmistakable and one click exits back to
the operator dashboard. Universal across all client templates — no per-template
edits required.

ClientActivityTracker — lightweight usage instrumentation for real clients:
authenticated non-staff hits on /projects/<pk>/ paths stamp the matching
OrganizationMember row's ``last_seen_at`` and bump ``page_views``, throttled to
one write per 10-minute active window (the throttle lives in the UPDATE's WHERE
clause, so it costs a single query and is race-safe).
"""
import re
from datetime import timedelta

from django.db.models import F, Q
from django.utils import timezone

from openoutreach.core.models import OrganizationMember, Project

_BANNER = (
    '<div style="position:sticky;top:0;z-index:99999;background:#0b1730;color:#fff;'
    'display:flex;align-items:center;justify-content:center;gap:16px;padding:9px 16px;'
    'font-family:Inter,system-ui,sans-serif;font-size:13px;font-weight:600;'
    'border-bottom:2px solid #D4A017;">'
    '<span style="color:#e5ad3f;">&#128065; Viewing as client &mdash; {org}</span>'
    '<a href="/operator/organizations/{pk}/" style="color:#fff;background:rgba(255,255,255,.16);'
    'padding:5px 14px;border-radius:99px;text-decoration:none;font-weight:700;">Exit view-as-client</a>'
    "</div>"
)


class ViewAsClientBanner:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            user = getattr(request, "user", None)
            match = getattr(request, "resolver_match", None)
            if not (user and user.is_authenticated and user.is_staff):
                return response
            if not match or not (match.url_name or "").startswith("project-"):
                return response
            pk = match.kwargs.get("pk")
            if not pk or "text/html" not in response.get("Content-Type", ""):
                return response
            if not hasattr(response, "content"):
                return response
            project = Project.objects.select_related("organization").filter(pk=pk).first()
            if not project or project.users.filter(pk=user.pk).exists():
                return response  # owner — normal client, no banner

            banner = _BANNER.format(org=project.organization.name, pk=pk).encode()
            content = response.content
            idx = content.lower().find(b"<body")
            if idx == -1:
                return response
            insert_at = content.find(b">", idx) + 1
            response.content = content[:insert_at] + banner + content[insert_at:]
            if response.has_header("Content-Length"):
                response["Content-Length"] = str(len(response.content))
        except Exception:
            pass  # a banner failure must never break the page
        return response


# One activity "window": at most one last_seen_at write (and one page_views
# increment) per member per window, no matter how many pages they click through.
ACTIVITY_THROTTLE = timedelta(minutes=10)

_PROJECT_PATH = re.compile(r"^/projects/(\d+)/")


class ClientActivityTracker:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            self._track(request)
        except Exception:
            pass  # instrumentation must never break the page
        return response

    @staticmethod
    def _track(request):
        user = getattr(request, "user", None)
        if not (user and user.is_authenticated) or user.is_staff:
            return
        match = _PROJECT_PATH.match(request.path)
        if not match:
            return
        now = timezone.now()
        OrganizationMember.objects.filter(
            user=user, project_id=int(match.group(1)),
        ).filter(
            Q(last_seen_at__isnull=True) | Q(last_seen_at__lt=now - ACTIVITY_THROTTLE)
        ).update(last_seen_at=now, page_views=F("page_views") + 1)
