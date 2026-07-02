"""Cost field on ResourceProvider: surfaces honestly on the resources page,
and the seed command is idempotent."""

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse

from openoutreach.core.models import Organization, Project
from openoutreach.funding.models import ResourceProvider


@pytest.fixture
def project_with_user(db):
    user = get_user_model().objects.create_user(username="cost-viewer", password="password")
    organization = Organization.objects.create(
        name="Cost Test Org",
        website="https://cost-test.example",
        mission="Testing cost labels.",
        organization_type="Nonprofit",
    )
    project = Project.objects.create(organization=organization, name="Cost Project")
    project.users.add(user)
    return project, user


def test_cost_labels_surface_on_resources_page(client, project_with_user):
    project, user = project_with_user
    ResourceProvider.objects.create(
        name="Totally Free Thing",
        website="https://free-thing.org",
        cost=ResourceProvider.ResourceCost.FREE,
        active=True,
    )
    ResourceProvider.objects.create(
        name="Cheap Thing",
        website="https://cheap-thing.org",
        cost=ResourceProvider.ResourceCost.LOW_COST,
        active=True,
    )
    ResourceProvider.objects.create(
        name="Expensive Thing",
        website="https://expensive-thing.org",
        cost=ResourceProvider.ResourceCost.PAID,
        active=True,
    )
    client.force_login(user)
    response = client.get(reverse("project-resources", kwargs={"pk": project.pk}))
    content = response.content.decode()

    assert response.status_code == 200
    # The old hardcoded blanket label is gone; each row carries its real cost.
    assert "Free / Low-cost" not in content
    assert 'class="impact-label cost-badge cost-free"' in content
    assert 'class="impact-label cost-badge cost-low_cost"' in content
    assert 'class="impact-label cost-badge cost-paid"' in content
    assert "Paid" in content


def test_seed_capacity_resources_idempotent(db):
    # Simulate the production duplicate TechSoup rows so dedupe is exercised.
    ResourceProvider.objects.create(
        name="TechSoup — Nonprofit Software Donations", website="https://www.techsoup.org", active=True,
    )
    ResourceProvider.objects.create(name="TechSoup", website="https://www.techsoup.org/", active=True)

    call_command("seed_capacity_resources")
    first_count = ResourceProvider.objects.count()
    first_active = ResourceProvider.objects.filter(active=True).count()

    digitunity = ResourceProvider.objects.get(website__icontains="digitunity.org")
    assert digitunity.cost == ResourceProvider.ResourceCost.FREE
    assert digitunity.active

    call_command("seed_capacity_resources")
    assert ResourceProvider.objects.count() == first_count
    assert ResourceProvider.objects.filter(active=True).count() == first_active

    # Exactly one active TechSoup row survives seeding.
    techsoup_active = ResourceProvider.objects.filter(
        active=True, website__icontains="techsoup.org"
    ).count()
    assert techsoup_active == 1
