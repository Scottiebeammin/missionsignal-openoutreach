import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from openoutreach.signals.demo import seed_missionsignal_demo


pytestmark = pytest.mark.django_db


@pytest.fixture
def celebrations_project(db):
    user, _organization, project = seed_missionsignal_demo()
    return project, user


def test_project_member_can_view_celebrations_page(client, celebrations_project):
    project, user = celebrations_project
    client.force_login(user)

    response = client.get(reverse("project-celebrations", kwargs={"pk": project.pk}))

    assert response.status_code == 200
    content = response.content.decode()
    assert "Wins Across the Web" in content
    assert "Impact Highlights" in content
    assert "Share a Win" in content
    assert "Momentum Across the Ecosystem" in content
    assert "Recent Celebration Feed" in content


def test_non_member_cannot_view_celebrations_page(client, celebrations_project):
    project, _user = celebrations_project
    outsider = get_user_model().objects.create_user(username="celebrations-outsider")
    client.force_login(outsider)

    response = client.get(reverse("project-celebrations", kwargs={"pk": project.pk}))

    assert response.status_code == 404


def test_celebrations_page_renders_seeded_examples_and_metrics(client, celebrations_project):
    project, user = celebrations_project
    client.force_login(user)

    response = client.get(reverse("project-celebrations", kwargs={"pk": project.pk}))

    content = response.content.decode()
    assert "Digital Equity Grant Awarded" in content
    assert "New Workforce Partnership" in content
    assert "Technology Access Milestone" in content
    assert "Community Health Success Story" in content
    assert "Strategic Introduction to City Workforce Leaders" in content
    assert "Community Collaboration with Digital Inclusion Partners" in content
    assert "Celebrations shared" in content
    assert "Opportunities awarded" in content
    assert "Partnerships formed" in content
    assert "Impact stories shared" in content


def test_global_footer_and_navigation_render_on_celebrations_page(client, celebrations_project):
    project, user = celebrations_project
    client.force_login(user)

    response = client.get(reverse("project-celebrations", kwargs={"pk": project.pk}))

    content = response.content.decode()
    assert "Anansi Atlas" in content
    assert "The Web of Opportunity" in content
    assert "anansiatlas.com" in content
    assert "Anansi Atlas is operated by Scott Foundry Group LLC." in content
    assert "Dashboard" in content
    assert "Readiness" in content
    assert "Documents" in content
    assert "Evidence" in content
    assert "Celebrations" in content
    assert "Workspace Settings" in content
