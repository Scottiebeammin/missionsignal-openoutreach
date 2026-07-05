"""
Project invite links.

The founder generates a signed, expiring URL for a specific project
(`manage.py create_invite --project-id N`), sends it to the client, and the
client picks their own email + password. The new account is attached to the
project and logged straight into the portal. This is the only self-serve path
that grants project membership — public signup (`/accounts/signup/`) creates
UNVERIFIED accounts that stop at the activation paywall. Unlike public signup,
a token-holder may claim a webhook-provisioned password-less account by email
(the founder's signed link is the authorization); accounts that already have a
password are told to sign in.
"""

from django import forms
from django.contrib.auth import get_user_model, login
from django.contrib.auth.password_validation import validate_password
from django.core import signing
from django.shortcuts import redirect, render

from openoutreach.core.models import Project
from openoutreach.signals.notifications import ANANSI_ATLAS_OPERATOR_EMAIL, logger

INVITE_SALT = "anansi-project-invite"
INVITE_MAX_AGE_DAYS = 14


def make_invite_token(project_id: int) -> str:
    return signing.dumps({"project_id": project_id}, salt=INVITE_SALT)


def read_invite_token(token: str) -> int | None:
    """Return the project id, or None if the token is invalid/expired."""
    try:
        data = signing.loads(token, salt=INVITE_SALT, max_age=INVITE_MAX_AGE_DAYS * 86400)
    except signing.BadSignature:
        return None
    return data.get("project_id")


class InviteAcceptForm(forms.Form):
    first_name = forms.CharField(label="First name", max_length=150)
    last_name = forms.CharField(label="Last name", max_length=150, required=False)
    email = forms.EmailField(label="Work email")
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput)

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        existing = get_user_model().objects.filter(email__iexact=email).first()
        if existing and existing.has_usable_password():
            raise forms.ValidationError(
                "An account with this email already exists — sign in instead, "
                "or use the password reset link on the sign-in page."
            )
        return email

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Passwords don't match.")
        elif p1:
            validate_password(p1)
        return cleaned


def accept_invite(request, token):
    project_id = read_invite_token(token)
    project = Project.objects.filter(pk=project_id).select_related("organization").first() if project_id else None
    if project is None:
        return render(request, "signals/invite_invalid.html", status=410)

    if request.method == "POST":
        form = InviteAcceptForm(request.POST)
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
            user.first_name = form.cleaned_data["first_name"]
            user.set_password(form.cleaned_data["password1"])
            user.save()
            project.users.add(user)
            logger.info("Invite accepted: %s joined project %s (%s)", email, project.pk, project.organization.name)
            login(request, user)
            return redirect("project-dashboard", pk=project.pk)
    else:
        form = InviteAcceptForm()

    return render(request, "signals/invite_accept.html", {
        "form": form,
        "project": project,
        "organization": project.organization,
    })
