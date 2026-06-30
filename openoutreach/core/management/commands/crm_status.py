"""Read-only pipeline snapshot for voice/agent briefings.

Used by the Hermes 'openoutreach-crm' skill so the assistant (Mike) can answer
pipeline questions out loud without touching data. Read-only by construction:
it only runs ORM aggregates and prints. Postgres/SQLite-safe (no raw SQL).

    python manage.py crm_status            # human-readable briefing
    python manage.py crm_status --json      # machine-readable
    python manage.py crm_status --days 14    # widen the "recent" window
"""
import json
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Count
from django.utils import timezone

from openoutreach.crm.models import Deal, Lead
from openoutreach.core.models import Campaign


class Command(BaseCommand):
    help = "Read-only pipeline snapshot (deal counts by state/outcome/campaign)."

    def add_arguments(self, parser):
        parser.add_argument("--json", action="store_true", help="Emit JSON instead of prose.")
        parser.add_argument("--days", type=int, default=7, help="Recent-activity window (days).")

    def handle(self, *args, **opts):
        days = opts["days"]
        since = timezone.now() - timedelta(days=days)

        by_state = {r["state"]: r["n"] for r in
                    Deal.objects.values("state").annotate(n=Count("id")).order_by()}
        by_outcome = {r["outcome"]: r["n"] for r in
                      Deal.objects.exclude(outcome="").values("outcome").annotate(n=Count("id")).order_by()}

        campaigns = []
        for c in Campaign.objects.all():
            cs = {r["state"]: r["n"] for r in
                  Deal.objects.filter(campaign=c).values("state").annotate(n=Count("id")).order_by()}
            campaigns.append({
                "campaign": getattr(c, "name", str(c)),
                "total": sum(cs.values()),
                "by_state": cs,
            })

        data = {
            "generated": timezone.now().isoformat(),
            "totals": {"leads": Lead.objects.count(), "deals": Deal.objects.count()},
            "by_state": by_state,
            "by_outcome": by_outcome,
            "recent": {
                "window_days": days,
                "deals_updated": Deal.objects.filter(update_date__gte=since).count(),
                "new_deals": Deal.objects.filter(creation_date__gte=since).count(),
            },
            "campaigns": campaigns,
        }

        if opts["json"]:
            self.stdout.write(json.dumps(data, indent=2))
            return

        t = data["totals"]
        out = [
            "OpenOutreach pipeline snapshot",
            f"  Leads: {t['leads']}   Deals: {t['deals']}",
            "",
            "  By state:",
        ]
        for state, n in by_state.items():
            out.append(f"    {state}: {n}")
        if by_outcome:
            out.append("")
            out.append("  Outcomes set:")
            for oc, n in by_outcome.items():
                out.append(f"    {oc}: {n}")
        r = data["recent"]
        out += [
            "",
            f"  Last {r['window_days']} days: {r['new_deals']} new deals, {r['deals_updated']} updated",
        ]
        if campaigns:
            out.append("")
            out.append("  By campaign:")
            for c in campaigns:
                out.append(f"    {c['campaign']}: {c['total']} deals")
        self.stdout.write("\n".join(out))
