"""
Management command: send_opportunity_alerts

Daily digest to each project owner:
  - UPCOMING DEADLINES: relevant, US-eligible, not-yet-applied opportunities whose
    deadline lands exactly 14 / 7 / 3 / 1 days out (stateless milestone reminders —
    each opp fires at most once per milestone, no per-row tracking needed).
  - NEW MATCHES: relevant opportunities created in the last ~24h (i.e. since the last
    daily run, typically right after the Grants.gov refresh).

Run after the data refresh, e.g.:
  python manage.py pull_grants_gov --all && python manage.py send_opportunity_alerts
  python manage.py send_opportunity_alerts --dry-run
  python manage.py send_opportunity_alerts --window 26   # hours for "new" (default 26)
"""
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

_DEADLINE_MILESTONES = {14, 7, 3, 1}


class Command(BaseCommand):
    help = "Email project owners about upcoming deadlines and newly-matched grants."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Print what would send; no emails")
        parser.add_argument("--window", type=int, default=26, help="Hours back to count 'new matches'")

    def handle(self, *args, **options):
        from openoutreach.core.models import Project
        from openoutreach.funding.models import Opportunity
        from openoutreach.funding.relevance import (
            org_keywords, opportunity_relevance, is_off_geography, is_research_grant,
        )
        from openoutreach.signals.notifications import send_opportunity_alert

        applied_status = {
            Opportunity.Status.APPLIED, Opportunity.Status.WON,
            Opportunity.Status.EXPIRED, Opportunity.Status.ARCHIVED,
        }
        applied_lifecycle = {
            Opportunity.LifecycleStatus.SUBMITTED, Opportunity.LifecycleStatus.AWARDED,
            Opportunity.LifecycleStatus.DECLINED, Opportunity.LifecycleStatus.CLOSED,
        }
        today = date.today()
        cutoff = timezone.now() - timedelta(hours=options["window"])
        dry = options["dry_run"]
        sent = 0

        for project in Project.objects.filter(active=True).select_related("organization"):
            owners = [u for u in project.users.all() if u.email]
            if not owners:
                continue
            keywords = org_keywords(project.organization)
            opps = list(Opportunity.objects.filter(project=project))

            deadline_items, new_matches = [], []
            for o in opps:
                if is_off_geography(o, project.organization) or is_research_grant(o):
                    continue
                if opportunity_relevance(o, keywords) <= 0:
                    continue
                # deadline milestone (only if not already applied/terminal)
                applied = o.status in applied_status or o.lifecycle_status in applied_lifecycle
                if o.deadline and not applied:
                    days = (o.deadline - today).days
                    if days in _DEADLINE_MILESTONES:
                        deadline_items.append((o, days))
                # new match
                if o.created_at and o.created_at >= cutoff:
                    new_matches.append(o)

            if not deadline_items and not new_matches:
                continue

            deadline_items.sort(key=lambda t: t[1])
            label = f"{project.organization.name}: {len(deadline_items)} deadline(s), {len(new_matches)} new"
            for owner in owners:
                if dry:
                    self.stdout.write(f"  [dry] -> {owner.email} | {label}")
                else:
                    if send_opportunity_alert(owner, project, new_matches, deadline_items):
                        sent += 1
                        self.stdout.write(self.style.SUCCESS(f"  sent -> {owner.email} | {label}"))

        if dry:
            self.stdout.write(self.style.WARNING("\nDry run — no emails sent."))
        else:
            self.stdout.write(self.style.SUCCESS(f"\nDone. {sent} alert email(s) sent."))
