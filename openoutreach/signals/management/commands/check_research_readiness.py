"""Is the cold list actually ready to draft against?

Run this after deploying and after ``seed_lead_intel``, before any redraft.

The failure it exists to catch is silent. ``research_profile`` replaced ``notes`` as
the only prose field the writer trusts, so between deploying that change and
re-running the command that populates it, every lead still has its research — just
in a field nothing reads. The drafts still generate. They are simply written from
the organization's name and sector again, which is the exact regression that
produced a diabetes camp being pitched an after-school grant.

From inside the prompt "stranded" and "never researched" look identical. From out
here they do not: a lead with legacy notes and an empty research_profile is a
deployment mistake, and a lead with neither is an honest thin profile.

    python manage.py check_research_readiness
    python manage.py check_research_readiness --segment cold_florida_crm
"""
from __future__ import annotations

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Report whether cold leads have verified research the writer can actually use."

    def add_arguments(self, parser):
        parser.add_argument("--segment", default="cold_florida_crm",
                            help="Lead segment to check (default: cold_florida_crm). 'all' for every segment.")
        parser.add_argument("--quiet", action="store_true",
                            help="Print only the summary counts and the exit verdict.")

    def handle(self, *args, **options):
        from openoutreach.core.management.commands.preview_cohort_drafts import research_gap
        from openoutreach.signals.models import SalesLead

        qs = SalesLead.objects.exclude(email="")
        if options["segment"] != "all":
            qs = qs.filter(list_segment=options["segment"])
        # A lead that cannot be sent to is not a readiness problem — it is a decision.
        leads = [l for l in qs.order_by("pk") if not l.cold_outreach_block()]

        stranded, thin, ready = [], [], []
        for lead in leads:
            if research_gap(lead):
                stranded.append(lead)
            elif not lead.research_profile:
                thin.append(lead)
            else:
                ready.append(lead)

        if not options["quiet"]:
            for label, group, style in (
                ("STRANDED — research is in legacy notes, the writer will not see it",
                 stranded, self.style.ERROR),
                ("THIN — no research on file; category-relevant outreach is legitimate",
                 thin, self.style.WARNING),
            ):
                if not group:
                    continue
                self.stdout.write(style(f"\n{label}:"))
                for lead in group:
                    self.stdout.write(f"  #{lead.pk:<5} {(lead.organization or lead.name)[:52]}")

        held = [l for l in qs if l.cold_outreach_block()]
        self.stdout.write("")
        self.stdout.write(f"ready:     {len(ready):>4}  research_profile present")
        self.stdout.write(f"thin:      {len(thin):>4}  no research anywhere (fine — writes category-relevant)")
        self.stdout.write(f"stranded:  {len(stranded):>4}  research in legacy notes only")
        self.stdout.write(f"held:      {len(held):>4}  disqualified or under review (excluded above)")

        if stranded:
            self.stderr.write(self.style.ERROR(
                f"\nNOT READY. {len(stranded)} lead(s) would be drafted as though nothing were "
                "known about them, while their research sits in `notes`.\n"
                "Run `python manage.py seed_lead_intel`, then re-run this check.\n"
                "Drafting is held for these leads unless --allow-missing-research is passed."))
            return
        self.stdout.write(self.style.SUCCESS("\nREADY — no lead has research stranded in legacy notes."))
