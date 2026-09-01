"""The dashboard must never show a client a grant whose deadline has passed.

Regression cover for the 2026-08-31 finding: `expire_opportunities` is manual, so a
closed grant stays `active` until someone remembers to sweep. The pipeline board gets
away with it because its view runs the sweep on load; the dashboard had no such
protection, and its UPCOMING DEADLINES panel sorts by deadline ascending — so the
longest-dead grants sorted straight to the top of a founding partner's board.

These tests pin the guarantee to the date, not to whether a sweep has run.
"""
import datetime

import pytest
from django.utils import timezone

from openoutreach.core.models import Organization, Project
from openoutreach.funding.models import Opportunity
from openoutreach.signals.dashboard import _relevant_upcoming_deadlines


@pytest.fixture
def youth_project(db):
    organization = Organization.objects.create(
        name="Riverbend Girls Collective",
        website="https://riverbend.example",
        mission="Youth development and mentoring for girls ages 9 to 18.",
        city="Orlando",
        county="Orange",
        state="Florida",
    )
    return Project.objects.create(
        organization=organization,
        name="Opportunity Web",
        programs="Youth development, mentoring, and after-school programming for girls.",
    )


def _make(project, name, deadline, status=Opportunity.Status.ACTIVE):
    return Opportunity.objects.create(
        project=project,
        name=name,
        opportunity_type="grant",
        status=status,
        deadline=deadline,
        geography="Orange County, Florida",
        focus_areas=["Youth Development"],
    )


@pytest.mark.django_db
def test_past_deadline_is_hidden_even_when_never_swept(youth_project):
    """The exact production shape: deadline passed, status still ACTIVE, no sweep run."""
    today = timezone.localdate()
    stale = _make(
        youth_project,
        "Youth Development General Grant",
        today - datetime.timedelta(days=26),
    )
    assert stale.status == Opportunity.Status.ACTIVE  # nothing swept it

    shown = _relevant_upcoming_deadlines(youth_project)

    assert stale not in shown, "a closed grant reached a client's dashboard"


@pytest.mark.django_db
def test_future_deadline_is_still_shown(youth_project):
    """The guard must not empty the panel — future work still surfaces."""
    today = timezone.localdate()
    live = _make(
        youth_project,
        "Youth Mentoring Program Grant",
        today + datetime.timedelta(days=30),
    )

    assert live in _relevant_upcoming_deadlines(youth_project)


@pytest.mark.django_db
def test_today_is_still_actionable(youth_project):
    """A deadline of *today* has not passed — the client can still act on it."""
    due_today = _make(youth_project, "Youth Development General Grant", timezone.localdate())

    assert due_today in _relevant_upcoming_deadlines(youth_project)


@pytest.mark.django_db
def test_panel_leads_with_the_soonest_live_deadline(youth_project):
    """Ordering survives the filter, and a dead row cannot take the top slot."""
    today = timezone.localdate()
    _make(youth_project, "Youth Development General Grant", today - datetime.timedelta(days=40))
    soonest = _make(
        youth_project, "Youth Mentoring Program Grant", today + datetime.timedelta(days=3)
    )
    _make(
        youth_project,
        "Youth Empowerment Program Grant",
        today + datetime.timedelta(days=60),
    )

    shown = _relevant_upcoming_deadlines(youth_project)

    assert shown, "panel unexpectedly empty"
    assert shown[0] == soonest
    assert all(o.deadline >= today for o in shown)
