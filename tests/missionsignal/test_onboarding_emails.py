"""EGI's two onboarding emails: the seat-welcome (join links + Dashboard
Walkthrough video) and the who-we-are email (WhoWeAre video, from marcus@)."""
import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command

from openoutreach.core.models import Organization, Project

pytestmark = pytest.mark.django_db


def test_seat_welcome_carries_dashboard_walkthrough_video():
    from openoutreach.signals.billing import _send_seat_welcome
    user = get_user_model().objects.create_user(username="ed@egi.org", email="ed@egi.org", first_name="Dana")
    _send_seat_welcome(user, scheduling_url="https://cal.com/marcus/x")
    msg = mail.outbox[0]
    body = msg.body
    assert "AL7wfKWrlAk" in body            # the Dashboard Walkthrough
    assert "FBvLg9c35Qo" not in body        # NOT the who-we-are video
    assert "Set your password" in body      # the join links
    assert msg.from_email == "info@anansiatlas.com"      # seat email sends from info@
    assert msg.bcc == ["marcus@anansiatlas.com"]         # copy lands in Marcus's inbox


def test_who_we_are_email_carries_explainer_and_from_marcus():
    org = Organization.objects.create(name="Empowered Girls Inc.", mission="Serve girls.")
    project = Project.objects.create(name="Empowered Girls Inc.", organization=org)
    user = get_user_model().objects.create_user(username="ed@egi.org", email="ed@egi.org", first_name="Dana")
    project.users.add(user)

    call_command("send_who_we_are", "--project-id", str(project.pk))
    msg = mail.outbox[0]
    assert msg.to == ["ed@egi.org"]
    assert "FBvLg9c35Qo" in msg.body        # the WhoWeAre explainer
    assert "AL7wfKWrlAk" not in msg.body    # NOT the dashboard walkthrough
    assert msg.from_email == "marcus@anansiatlas.com"   # warm → marcus@
    assert "Empowered Girls Inc." in msg.body


def test_who_we_are_dry_run_sends_nothing():
    org = Organization.objects.create(name="EGI", mission="x")
    project = Project.objects.create(name="EGI", organization=org)
    user = get_user_model().objects.create_user(username="a@egi.org", email="a@egi.org")
    project.users.add(user)
    call_command("send_who_we_are", "--project-id", str(project.pk), "--dry-run")
    assert len(mail.outbox) == 0
