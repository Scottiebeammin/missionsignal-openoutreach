from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse

from openoutreach.core.models import Organization, Project
from openoutreach.funding.models import FundingCriteria
from openoutreach.signals.demo import (
    DEMO_ORGANIZATION_NAME,
    DEMO_USERNAME,
    seed_missionsignal_demo,
)
from openoutreach.signals.models import OrganizationAnalysisRun


@pytest.mark.django_db
def test_demo_seed_is_idempotent_and_analysis_ready():
    first_user, first_organization, first_project = seed_missionsignal_demo()
    second_user, second_organization, second_project = seed_missionsignal_demo()

    assert first_user == second_user
    assert first_organization == second_organization
    assert first_project == second_project
    assert get_user_model().objects.filter(username=DEMO_USERNAME).count() == 1
    assert Organization.objects.filter(name=DEMO_ORGANIZATION_NAME).count() == 1
    assert Project.objects.filter(
        organization=first_organization, name="Primary Initiative",
    ).count() == 1
    assert first_organization.organization_summary
    assert first_organization.focus_areas
    assert first_organization.city == "Cleveland"
    assert FundingCriteria.objects.filter(project=first_project).count() == 1
    assert OrganizationAnalysisRun.objects.filter(
        organization=first_organization,
    ).count() == 2


@pytest.mark.django_db
def test_demo_seed_command_prints_demo_routes_and_sets_password():
    output = StringIO()

    call_command("seed_missionsignal_demo", password="demo-password", stdout=output)

    user = get_user_model().objects.get(username=DEMO_USERNAME)
    project = Project.objects.get(name="Primary Initiative")
    command_output = output.getvalue()
    assert user.check_password("demo-password")
    assert "MissionSignal demo data is ready." in command_output
    assert reverse("project-analysis-detail", kwargs={"pk": project.pk}) in command_output
    assert reverse("project-mission-brief", kwargs={"pk": project.pk}) in command_output
