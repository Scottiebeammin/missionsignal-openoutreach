"""expire_opportunities: sweep past-deadline grants off every project's board, not
just the one project someone happened to open."""
from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone

from openoutreach.core.models import Organization, Project
from openoutreach.funding.models import Opportunity

pytestmark = pytest.mark.django_db


def _project(name):
    organization = Organization.objects.create(name=name, mission="Serve the community.")
    return Project.objects.create(name=name, organization=organization)


def _opportunity(project, name, days, **kwargs):
    return Opportunity.objects.create(
        project=project,
        name=name,
        deadline=timezone.localdate() + timedelta(days=days),
        **kwargs,
    )


def test_expires_past_deadline_rows_across_every_project():
    first, second = _project("Women on the Rise"), _project("Empowered Girls")
    _opportunity(first, "Closed last week", days=-7)
    _opportunity(second, "Closed yesterday", days=-1)
    open_still = _opportunity(second, "Still open", days=10)

    out = StringIO()
    call_command("expire_opportunities", stdout=out)

    assert "Expired 2" in out.getvalue()
    assert Opportunity.objects.get(name="Closed last week").status == Opportunity.Status.EXPIRED
    assert Opportunity.objects.get(name="Closed yesterday").status == Opportunity.Status.EXPIRED
    open_still.refresh_from_db()
    assert open_still.status == Opportunity.Status.ACTIVE


def test_leaves_applied_and_archived_work_alone():
    project = _project("Women on the Rise")
    applied = _opportunity(project, "Submitted in time", days=-3, status=Opportunity.Status.APPLIED)
    archived = _opportunity(project, "Retracted row", days=-3, status=Opportunity.Status.ARCHIVED)
    submitted = _opportunity(
        project, "Submitted lifecycle", days=-3,
        lifecycle_status=Opportunity.LifecycleStatus.SUBMITTED,
    )

    call_command("expire_opportunities", stdout=StringIO())

    for opportunity in (applied, archived, submitted):
        before = opportunity.status
        opportunity.refresh_from_db()
        assert opportunity.status == before


def test_dry_run_lists_without_changing_anything():
    project = _project("Women on the Rise")
    stale = _opportunity(project, "Closed last week", days=-7)

    out = StringIO()
    call_command("expire_opportunities", "--dry-run", stdout=out)

    assert "Closed last week" in out.getvalue()
    assert "would be expired" in out.getvalue()
    stale.refresh_from_db()
    assert stale.status == Opportunity.Status.ACTIVE


def test_project_flag_limits_the_sweep():
    first, second = _project("Women on the Rise"), _project("Empowered Girls")
    mine = _opportunity(first, "Mine", days=-7)
    theirs = _opportunity(second, "Theirs", days=-7)

    call_command("expire_opportunities", "--project", str(first.pk), stdout=StringIO())

    mine.refresh_from_db()
    theirs.refresh_from_db()
    assert mine.status == Opportunity.Status.EXPIRED
    assert theirs.status == Opportunity.Status.ACTIVE


def test_second_run_moves_nothing():
    project = _project("Women on the Rise")
    _opportunity(project, "Closed last week", days=-7)
    call_command("expire_opportunities", stdout=StringIO())

    out = StringIO()
    call_command("expire_opportunities", stdout=out)

    assert "Expired 0" in out.getvalue()
