# openoutreach/core/views.py
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect, render

from openoutreach.core.models import Project
from openoutreach.signals.models import PilotProfile


@login_required
def portal(request):
    project = (
        Project.objects.filter(users=request.user)
        .select_related("organization")
        .first()
    )

    pilot = None
    if project is not None:
        pilot = getattr(project, "pilot_profile", None)

    return render(request, "core/portal.html", {
        "project": project,
        "pilot": pilot,
    })


def signup(request):
    if request.user.is_authenticated:
        return redirect("portal")
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("portal")
    else:
        form = UserCreationForm()
    return render(request, "core/signup.html", {"form": form})
