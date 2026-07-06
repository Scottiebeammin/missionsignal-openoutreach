"""setup_egi_seats: prep EGI's 2 founding seats + invite link, and add existing
project users to the Founding Partners group (so the welcome hero shows)."""
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command

from openoutreach.core.access import founding_partners_group
from openoutreach.core.models import Organization, Project

pytestmark = pytest.mark.django_db


def test_prints_invite_and_promotes_users_to_founding():
    org = Organization.objects.create(name="Empowered Girls Inc.", mission="Serve girls 9-18.")
    project = Project.objects.create(name="Empowered Girls Inc.", organization=org)
    user = get_user_model().objects.create_user(username="ed@egi.org", email="ed@egi.org")
    project.users.add(user)

    out = StringIO()
    call_command("setup_egi_seats", stdout=out)
    text = out.getvalue()

    assert "/invite/" in text                       # ready-to-send link
    assert "Executive Director opens it FIRST" in text
    assert user.groups.filter(pk=founding_partners_group().pk).exists()  # welcome will show


def test_errors_without_egi():
    with pytest.raises(CommandError, match="No Empowered Girls"):
        call_command("setup_egi_seats")
