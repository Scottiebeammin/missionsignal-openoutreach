"""Client-side seat management: account admins invite and remove teammates
from the Team & Seats card, instead of the operator running create_invite.

- Invite mints a signed link (shown once, never persisted) that the existing
  accept_invite flow honors — the second seat joins as a non-admin.
- Remove drops a teammate seat; admins can't remove an admin seat or themselves.
- Both actions are admin-gated (403 for non-admin members and outsiders).
"""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from openoutreach.core.models import Organization, OrganizationMember, Project

pytestmark = pytest.mark.django_db


@pytest.fixture
def project(db):
    org = Organization.objects.create(name="Empowered Girls Inc.", mission="Serve girls 9-18.")
    return Project.objects.create(name="Empowered Girls Inc.", organization=org)


@pytest.fixture
def admin_seat(project):
    user = get_user_model().objects.create_user(username="ed@egi.org", email="ed@egi.org", password="x")
    project.users.add(user)
    OrganizationMember.objects.create(user=user, project=project, is_admin=True, contact_name="Executive Director")
    return user


@pytest.fixture
def member_seat(project):
    user = get_user_model().objects.create_user(username="staff@egi.org", email="staff@egi.org", password="x")
    project.users.add(user)
    return OrganizationMember.objects.create(user=user, project=project, is_admin=False, contact_name="Program Lead")


def test_admin_invite_shows_link_and_accept_creates_second_seat(client, project, admin_seat):
    client.force_login(admin_seat)
    response = client.post(reverse("project-invite-teammate", kwargs={"pk": project.pk}), follow=True)
    body = response.content.decode()
    assert "Invite link ready" in body
    assert "/invite/" in body

    # Pull the token out of the rendered link and accept it as a new person.
    import re
    token = re.search(r"/invite/([^/\"]+)/", body).group(1)
    accept = client.__class__()  # fresh client
    accept.post(f"/invite/{token}/", {
        "first_name": "Dana", "email": "dana@egi.org",
        "password1": "web-of-opportunity-9", "password2": "web-of-opportunity-9",
    }, HTTP_HOST="testserver")
    new_member = OrganizationMember.objects.get(user__email="dana@egi.org", project=project)
    assert new_member.is_admin is False  # second seat is not admin


def test_non_admin_cannot_invite(client, project, member_seat):
    client.force_login(member_seat.user)
    response = client.post(reverse("project-invite-teammate", kwargs={"pk": project.pk}))
    assert response.status_code == 403


def test_admin_removes_member_seat(client, project, admin_seat, member_seat):
    client.force_login(admin_seat)
    response = client.post(reverse("project-remove-seat", kwargs={"pk": project.pk, "member_id": member_seat.pk}))
    assert response.status_code == 302
    assert not OrganizationMember.objects.filter(pk=member_seat.pk).exists()
    assert not project.users.filter(pk=member_seat.user_id).exists()


def test_admin_cannot_remove_another_admin_or_self(client, project, admin_seat):
    admin_member = OrganizationMember.objects.get(user=admin_seat, project=project)
    # A second admin seat
    other = get_user_model().objects.create_user(username="co@egi.org", email="co@egi.org", password="x")
    project.users.add(other)
    other_admin = OrganizationMember.objects.create(user=other, project=project, is_admin=True)

    client.force_login(admin_seat)
    assert client.post(reverse("project-remove-seat", kwargs={"pk": project.pk, "member_id": other_admin.pk})).status_code == 403
    assert client.post(reverse("project-remove-seat", kwargs={"pk": project.pk, "member_id": admin_member.pk})).status_code == 403
    assert OrganizationMember.objects.filter(project=project).count() == 2


def test_non_admin_cannot_remove(client, project, admin_seat, member_seat):
    admin_member = OrganizationMember.objects.get(user=admin_seat, project=project)
    client.force_login(member_seat.user)
    response = client.post(reverse("project-remove-seat", kwargs={"pk": project.pk, "member_id": admin_member.pk}))
    assert response.status_code == 403


def test_invite_button_hidden_from_non_admin(client, project, member_seat):
    client.force_login(member_seat.user)
    body = client.get(reverse("project-organization", kwargs={"pk": project.pk})).content.decode()
    assert "Invite a teammate" not in body
