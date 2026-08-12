"""Promote a screened batch of market orgs into the cold pipeline.

The market browser's one-at-a-time "→ Pipeline" button is right for hand-picking;
this is for pulling a working batch. It applies the screen *before* promotion,
which is the cheap half of list hygiene: every row already comes from the IRS
exempt-org file (EIN + subsection), so legitimacy isn't the question — **fit**
is, and `FloridaOrg.ntee_sector` already carries it. Screening here is what keeps
a drag-racing museum or a worship centre out of a cold batch aimed at
direct-service nonprofits, for free, before anyone opens a website.

What's left after this screen is the expensive half — is the org still operating,
is the site up, is the contact real — and that's a human pass over a much smaller
set (see also `check_link_health` / `rescan_websites`).

Promotion itself goes through `signals.market.promote_org_to_pipeline`, so it
stays idempotent (the `promoted_lead` FK guards a second call) and keeps the
provenance notes. This command adds one thing the shared path doesn't: it sets
`SalesLead.focus_area` from the org's NTEE sector, which the cold sequence's
`{{focus_area}}` token needs.

Preview by default — nothing is written unless you pass --commit.

    # what would a screened Orange County batch of 20 look like?
    python manage.py promote_market_batch --county ORANGE --limit 20

    # do it
    python manage.py promote_market_batch --county ORANGE --limit 20 --commit

    # widen or narrow the screen
    python manage.py promote_market_batch --county ORANGE --sector "Arts, culture, humanities" --commit
"""
from __future__ import annotations

import urllib.parse

from django.core.management.base import BaseCommand
from django.db.models import Q

# Direct-service sectors — the organizations Anansi Atlas is actually for.
# Deliberately excluded from the default: "Religion-related" and
# "Recreation / sports" (wrong buyer), "Animal-related", "Philanthropy /
# grantmaking" (those are funders, not seat buyers), and "Unknown /
# unclassified" — the largest bucket in the data, but fit can't be verified from
# the row, so it needs eyes rather than a default. Add any of them back with
# --sector; see --include-unclassified for that last one.
DEFAULT_SECTORS = [
    "Human services",
    "Education",
    "Youth development",
    "Health care",
    "Mental health",
    "Housing / shelter",
    "Employment",
    "Food / agriculture",
    "Community improvement",
]
UNCLASSIFIED = "Unknown / unclassified"

# Revenue band, straight from the outreach-engine brief's ICP config
# (atlas_subscribers.revenue_band). Sector alone is not enough: without a band,
# "Education" in Orange County returns Rollins College and a university, and
# "Community improvement" returns a venture fund and a CDFI lender. None of them
# are a stretched Executive Director hunting for aligned funders. The band is
# what encodes "an organization Atlas is actually for."
DEFAULT_MIN_INCOME = 250_000
DEFAULT_MAX_INCOME = 5_000_000

# Placeholder addresses scraped off template websites — never real inboxes.
JUNK_EMAIL_FRAGMENTS = ("your@email", "example.com", "email@email", "@domain.")

# ── Schools track ────────────────────────────────────────────────────────────
# Charter and religious schools are a separate audience with a separate message,
# so they get their own track rather than being screened out of the nonprofit one.
#
# NTEE codes can't do this job: the sector is "Education" for all of them, and the
# codes scatter (Hope Charter is B29, Princeton House Charter is B28Z, Access
# Charter is B24, Orlando Torah is B24, Muslim Academy is B20). Only B29 actually
# means "charter school". So this classifies on the name, which is what the
# distinction is legible in — and it's a heuristic, which is exactly why the
# command previews before it writes.
CHARTER_MARKERS = ("charter",)
RELIGIOUS_MARKERS = (
    "torah", "christian", "muslim", "islamic", "catholic", "hebrew", "jewish",
    "baptist", "lutheran", "adventist", "biblical", "yeshiva", "parochial",
    "sda ", "st. ", "saint ", "holy ", "trinity", "grace ", "faith ",
)
# Higher ed, accreditors and professional societies also sit under Education and
# are not schools in the sense that matters here.
NOT_A_SCHOOL_MARKERS = (
    "university", "college", "association", "society", "institute",
    "scholarship", "foundation", "trades",
    # Ministerial and higher-religious training — these teach adults to lead
    # congregations, not children in classrooms, so they have neither the
    # programs nor the funding world this campaign is written for. Caught by a
    # Broward preview surfacing "Reformed Baptist Seminary".
    "seminary", "rabbinical", "divinity", "theological",
)


def _norm(name: str) -> str:
    """Normalize an org name for collision matching — case, punctuation, suffixes."""
    n = name.lower().strip()
    for junk in (",", ".", "'", '"', "&"):
        n = n.replace(junk, " " if junk == "&" else "")
    for suffix in (" inc", " incorporated", " llc", " corp", " corporation", " ltd", " co"):
        if n.endswith(suffix):
            n = n[: -len(suffix)]
    return " ".join(n.split())


def existing_lead_keys():
    """Names and emails already in the pipeline, in any segment.

    `promote_org_to_pipeline` only guards on `FloridaOrg.promoted_lead`, which is
    set when *this system* promotes an org. Leads that arrived another way — the
    warm campaign was imported from CSV — have no back-link, so the same
    organization can exist as a warm lead and be promoted again as a cold one.
    That would put a stranger's cold email in front of someone Marcus already has
    a relationship with. Matching on name catches what matching on email misses:
    a warm contact is a named person (khadesia.brown@…) while the market row
    usually holds a generic inbox (info@…), so the addresses differ even though
    the organization is the same.
    """
    from openoutreach.signals.models import SalesLead

    names, emails = set(), set()
    for org, email in SalesLead.objects.values_list("organization", "email"):
        if org:
            names.add(_norm(org))
        if email:
            emails.add(email.lower().strip())
    return names, emails


def classify_school(name: str) -> str | None:
    """Return 'Charter school', 'Religious school', or None if it isn't either."""
    n = f" {name.lower()} "
    if any(m in n for m in NOT_A_SCHOOL_MARKERS):
        return None
    if any(m in n for m in CHARTER_MARKERS):
        return "Charter school"
    if any(m in n for m in RELIGIOUS_MARKERS):
        return "Religious school"
    return None


class Command(BaseCommand):
    help = "Promote a sector-screened batch of FloridaOrg rows into the cold pipeline."

    def add_arguments(self, parser):
        parser.add_argument("--county", action="append", default=[],
                            help="County to draw from. Repeatable. Use 'all' for statewide. "
                                 "Default: ORANGE. Schools are thin in any single county — 5 in Broward, "
                                 "6 in Orange — so a statewide or multi-county pull is usually the right "
                                 "shape for that track.")
        parser.add_argument("--track", choices=["nonprofit", "schools"], default="nonprofit",
                            help="'nonprofit' = the direct-service ICP (default). 'schools' = charter and "
                                 "religious schools only, tagged so they can be worked as their own audience.")
        parser.add_argument("--sector", action="append", default=[],
                            help="NTEE sector to include. Repeatable. Replaces the default ICP set.")
        parser.add_argument("--include-unclassified", action="store_true",
                            help=f"Also include {UNCLASSIFIED!r} orgs — fit is unverified, so review these by hand.")
        parser.add_argument("--limit", type=int, default=20,
                            help="How many orgs to promote (default: 20 — one batch).")
        parser.add_argument("--min-income", type=int, default=DEFAULT_MIN_INCOME,
                            help=f"Minimum annual income (default: ${DEFAULT_MIN_INCOME:,} — the brief's ICP band).")
        parser.add_argument("--max-income", type=int, default=DEFAULT_MAX_INCOME,
                            help=f"Maximum annual income (default: ${DEFAULT_MAX_INCOME:,}). Above this you get "
                                 "colleges, hospital systems and funds, not the ICP.")
        parser.add_argument("--allow-no-email", action="store_true",
                            help="Include orgs with no direct email. They land in the call-list segment instead.")
        parser.add_argument("--exclude", action="append", default=[], metavar="RECORD_ID",
                            help="Drop a specific org by record_id (e.g. NP-011991). Repeatable — this is how "
                                 "you strike names off the preview before committing.")
        parser.add_argument("--commit", action="store_true",
                            help="Actually promote. Without this the command only prints what it would do.")

    def handle(self, *args, **options):
        from openoutreach.signals.market import promote_org_to_pipeline
        from openoutreach.signals.models import FloridaOrg, SalesLead

        schools_track = options["track"] == "schools"
        if schools_track:
            # Schools all sit under Education; classification happens on the name below.
            sectors = options["sector"] or ["Education"]
        else:
            sectors = options["sector"] or list(DEFAULT_SECTORS)
        if options["include_unclassified"]:
            sectors.append(UNCLASSIFIED)

        counties = [c.strip() for c in (options["county"] or ["ORANGE"])]
        statewide = any(c.lower() == "all" for c in counties)
        where = "FLORIDA (statewide)" if statewide else ", ".join(c.upper() for c in counties)

        qs = (
            FloridaOrg.objects
            .filter(ntee_sector__in=sectors)
            .filter(promoted_lead__isnull=True)  # never re-promote
            .filter(income_amount__gte=options["min_income"],
                    income_amount__lte=options["max_income"])
        )
        if not statewide:
            county_q = Q()
            for c in counties:
                county_q |= Q(county__iexact=c)
            qs = qs.filter(county_q)
        if options["exclude"]:
            qs = qs.exclude(record_id__in=[r.strip().upper() for r in options["exclude"]])
        if not options["allow_no_email"]:
            qs = qs.exclude(contact_email="")
            for fragment in JUNK_EMAIL_FRAGMENTS:
                qs = qs.exclude(contact_email__icontains=fragment)

        # Largest first *within the band* — a bigger budget in-band usually means
        # real programs and a real person reading the inbox.
        ordered = qs.order_by("-income_amount", "name")

        # (org, school_kind_or_None). On the schools track the name classifier is a
        # filter, so scan further than `limit` rather than truncating first.
        candidates: list[tuple[object, str | None]] = []
        from openoutreach.signals.management.commands.scrape_contact_emails import _is_foreign_domain

        known_names, known_emails = existing_lead_keys()
        skipped_known: list[str] = []
        flagged_foreign: set[str] = set()

        # The two tracks are mutually exclusive: a charter school promoted on the
        # nonprofit track would be worked with the wrong message, and whichever
        # track ran first would claim it (the promoted_lead FK is one-shot).
        for org in ordered[: options["limit"] * 20]:
            kind = classify_school(org.name)
            if schools_track and kind is None:
                continue
            if not schools_track and kind is not None:
                continue
            # Never cold-promote an organization that is already a lead — most
            # importantly a warm one. See existing_lead_keys().
            if _norm(org.name) in known_names or (org.contact_email or "").lower().strip() in known_emails:
                skipped_known.append(org.name)
                continue
            # Flag — don't drop — an email whose domain isn't the org's own. Some
            # are genuinely somebody else's (a web designer, a font foundry's
            # licence comment, usda.gov off a school-lunch page). But plenty are
            # the same organization under a second domain:
            # contact@victorychartertampa.org for victorychartertampa612.org is
            # the same school. Name similarity can't reliably tell those apart, so
            # the honest move is to surface it and let the preview do its job —
            # silently discarding a real school is the worse error.
            if org.contact_email and org.website and _is_foreign_domain(
                org.contact_email.split("@")[-1].lower(),
                urllib.parse.urlsplit(org.website).netloc.removeprefix("www.").lower(),
            ):
                flagged_foreign.add(org.record_id)
            candidates.append((org, kind if schools_track else None))
            if len(candidates) >= options["limit"]:
                break

        if skipped_known:
            self.stdout.write(self.style.WARNING(
                f"\nSkipped {len(skipped_known)} org(s) already in the pipeline — "
                "cold-emailing an existing (possibly warm) contact:"
            ))
            for n in skipped_known[:15]:
                self.stdout.write(f"    · {n}")



        if not candidates:
            self.stderr.write(self.style.ERROR(
                f"Nothing to promote in {where} for those sectors. "
                "Everything matching may already be promoted — or try --include-unclassified."
            ))
            return

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\n{len(candidates)} {options['track']} org(s) in {where} "
            f"{'to promote' if options['commit'] else '— PREVIEW, nothing written'}:\n"
        ))
        for org, kind in candidates:
            income = f"${org.income_amount:,}" if org.income_amount else "income unknown"
            label = kind or org.ntee_sector
            self.stdout.write(
                f"  {org.record_id}  {org.name[:44]:<44}  {label[:22]:<22}  {income}"
            )
            warn = "  ⚠ email is on a different domain — check it's the org's own" \
                if org.record_id in flagged_foreign else ""
            self.stdout.write(
                f"       {org.contact_email or '(no email)'}   {org.website or '(no website)'}{warn}"
            )

        if not options["commit"]:
            self.stdout.write(self.style.WARNING(
                "\nPreview only — nothing written. Re-run with --commit to promote.\n"
                "Check the names above first: this screen filters by sector, not by whether "
                "the organization is still operating."
            ))
            return

        promoted = 0
        for org, kind in candidates:
            segment = (
                SalesLead.Segment.COLD_FLORIDA_CRM if org.contact_email
                else SalesLead.Segment.COLD_CALL_LIST
            )
            lead, created = promote_org_to_pipeline(org, segment=segment)
            if not created:
                continue
            # The shared promote path doesn't set focus_area; the cold sequence's
            # {{focus_area}} token needs it. On the schools track this also carries
            # the audience tag — schools stay in the cold segment deliberately, so
            # they remain visible and sendable in the outreach cockpit (its tabs are
            # hardcoded to three segments, so a fourth would be invisible there).
            focus = kind or org.ntee_sector
            if focus and not lead.focus_area:
                lead.focus_area = focus
                lead.save(update_fields=["focus_area"])
            promoted += 1

        self.stdout.write(self.style.SUCCESS(
            f"\nPromoted {promoted} {options['track']} org(s) into the cold pipeline"
            + (" — tagged by school type in focus_area." if schools_track else ".")
            + "\nVerify they're still operating before drafting — screening can't tell you that."
        ))
