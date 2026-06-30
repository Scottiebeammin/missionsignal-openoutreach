"""View-as-client banner middleware.

When a staff operator opens a client's project portal (any `project-*` route) for a
project they don't personally belong to, inject a sticky banner so the "view as
client" mode is unmistakable and one click exits back to the operator dashboard.
Universal across all client templates — no per-template edits required.
"""
from openoutreach.core.models import Project

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
