# openoutreach/core/views.py
import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from openoutreach.core.models import OrganizationMember, Project
from openoutreach.signals.models import PilotProfile


@login_required
def portal(request):
    # Admins go straight to Django admin
    if request.user.is_staff:
        return redirect("/admin/")

    project = (
        Project.objects.filter(users=request.user)
        .select_related("organization")
        .first()
    )

    # No project yet — send to intake
    if project is None:
        return redirect("project-intake")

    member = OrganizationMember.objects.filter(user=request.user, project=project).first()

    # First-time login: send to snapshot so they see value immediately
    if member and not member.has_toured:
        return redirect("project-snapshot", pk=project.pk)

    return redirect("project-dashboard", pk=project.pk)


@login_required
@require_POST
def onboarding_mark_toured(request):
    project = Project.objects.filter(users=request.user).first()
    if project:
        OrganizationMember.objects.filter(user=request.user, project=project).update(has_toured=True)
    return JsonResponse({"ok": True})


@login_required
@require_POST
def onboarding_mark_page(request):
    try:
        data = json.loads(request.body)
        page_key = data.get("page", "")
    except (ValueError, KeyError):
        return JsonResponse({"ok": False}, status=400)

    project = Project.objects.filter(users=request.user).first()
    if project and page_key:
        member = OrganizationMember.objects.filter(user=request.user, project=project).first()
        if member:
            visited = list(member.visited_pages or [])
            if page_key not in visited:
                visited.append(page_key)
                member.visited_pages = visited
                member.save(update_fields=["visited_pages"])
    return JsonResponse({"ok": True})


def signup(request):
    # Public self-serve account creation is disabled while we gather interest first.
    # Anyone landing here is routed to the waitlist / schedule flow; access is granted
    # manually once an organization is onboarded. Already-signed-in users go to the portal.
    if request.user.is_authenticated:
        return redirect("portal")
    return redirect(reverse("anansi-atlas-landing") + "#get-started")
