# openoutreach/core/views.py
import json

from django import forms
from django.contrib.auth import get_user_model, login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from openoutreach.core.access import STRIPE_FOUNDING_SEAT_URL, user_is_verified
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

    # No project yet — verified (paid/invited) users go to intake; everyone
    # else hits the activation paywall.
    if project is None:
        if not user_is_verified(request.user):
            return redirect("account-activate")
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


class SignupForm(forms.Form):
    first_name = forms.CharField(label="First name", max_length=150)
    last_name = forms.CharField(label="Last name", max_length=150, required=False)
    email = forms.EmailField(label="Work email")
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput)

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        existing = get_user_model().objects.filter(email__iexact=email).first()
        if existing and existing.has_usable_password():
            raise forms.ValidationError("An account with this email already exists — sign in instead.")
        return email

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Passwords don't match.")
        elif p1:
            validate_password(p1)
        return cleaned


def signup(request):
    """Open self-serve account creation. New accounts are UNVERIFIED — the
    portal routes them to the activation paywall until they claim a founding
    seat (Stripe webhook verifies them) or receive an invite/manual grant."""
    if request.user.is_authenticated:
        return redirect("portal")
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            User = get_user_model()
            user = User.objects.filter(email__iexact=email).first()
            if user is None:
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    first_name=form.cleaned_data["first_name"],
                    last_name=form.cleaned_data.get("last_name", ""),
                )
            user.set_password(form.cleaned_data["password1"])
            user.first_name = form.cleaned_data["first_name"]
            user.save()
            auth_login(request, user)
            return redirect("portal")
    else:
        form = SignupForm()
    return render(request, "core/signup.html", {"form": form})


@login_required
def account_activate(request):
    """The activation paywall: account exists but isn't verified yet."""
    if user_is_verified(request.user):
        return redirect("portal")
    return render(request, "core/activate.html", {
        "stripe_url": STRIPE_FOUNDING_SEAT_URL,
    })
