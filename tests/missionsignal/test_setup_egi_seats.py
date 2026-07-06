"""setup_egi_seats: prep EGI's 2 founding seats + invite link, and add existing
project users to the Founding Partners group (so the welcome hero shows)."""
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command

from openoutreach.core.access import founding_partners_group
from openoutreach.core.models import Organization, Project

pytestmark = pytest.mark.django_db


def test_prints_two_links_and_promotes_users_to_founding():
    org = Organization.objects.create(name="Empowered Girls Inc.", mission="Serve girls 9-18.")
    project = Project.objects.create(name="Empowered Girls Inc.", organization=org)
    user = get_user_model().objects.create_user(username="ed@egi.org", email="ed@egi.org")
    project.users.add(user)

    out = StringIO()
    call_command("setup_egi_seats", stdout=out)
    text = out.getvalue()

    assert text.count("/invite/") == 2              # two distinct links
    assert "Executive Director (ADMIN)" in text
    assert "Program Lead (member)" in text
    assert user.groups.filter(pk=founding_partners_group().pk).exists()  # welcome will show


def test_admin_link_makes_admin_member_link_makes_member_regardless_of_order():
    from django.test import Client
    from openoutreach.core.models import OrganizationMember
    from openoutreach.signals.invites import make_invite_token

    org = Organization.objects.create(name="Two Seat Org", mission="Serve.")
    project = Project.objects.create(name="Two Seat Org", organization=org)
    admin_token = make_invite_token(project.pk, is_admin=True)
    member_token = make_invite_token(project.pk, is_admin=False)

    creds = {"password1": "web-of-opportunity-9", "password2": "web-of-opportunity-9"}
    # Program lead (member link) accepts FIRST — must NOT become admin.
    Client().post(f"/invite/{member_token}/", {"first_name": "Lead", "email": "lead@org.org", **creds}, HTTP_HOST="localhost")
    # ED (admin link) accepts SECOND — must be admin.
    Client().post(f"/invite/{admin_token}/", {"first_name": "ED", "email": "ed@org.org", **creds}, HTTP_HOST="localhost")

    members = {m.user.email: m for m in OrganizationMember.objects.filter(project=project)}
    assert members["ed@org.org"].is_admin is True
    assert members["lead@org.org"].is_admin is False


def test_errors_without_egi():
    with pytest.raises(CommandError, match="No Empowered Girls"):
        call_command("setup_egi_seats")
