"""Phase 2 validation: generate opener drafts for a handful of real orgs and read them.

The point of this command is to answer one question before any automation is trusted:
**do the drafts sound like Marcus?** If they don't, nothing upstream matters. If they do,
everything upstream is just feeding volume.

It renders the *same* ``email_opener.j2`` prompt and uses the *same* ``EmailDraft`` output
type as the production agent, so what you read here is what the engine would send. The
only thing that differs is where the context comes from: the real agent reads a
``Deal``/``Lead`` pair off a LinkedIn session, and this reads a ``SalesLead`` or
``FloridaOrg`` straight out of the Anansi pipeline — which is where the cohort audience
actually lives.

Read-only by default:
  - creates no Lead, no Deal, no Campaign
  - writes nothing back to any row
  - queues nothing to send

``--save`` opts into writing the draft onto the lead — ``subject_line`` and
``outreach_draft``, the two fields the operator cockpit's send flow already reads
(``signals/outreach.py``). That puts a generated batch into the review UI that
exists, rather than building a second one. It still queues nothing: the cockpit
sends only when the operator clicks send.

Batches, not blasts. The default sample skips leads that already have a draft, so
each run picks up where the last one left off — and the qualifier is an
*active-learning* model, so an operator's accept/reject decisions on batch N are
the training signal for batch N+1. Small batches are what makes it improve.

    # see the exact system prompt the model will get — no API key needed
    python manage.py preview_cohort_drafts --prompt-only

    # Phase 2 validation: read 5 drafts, save nothing
    python manage.py preview_cohort_drafts

    # a working batch of 20, saved into the cockpit for review
    python manage.py preview_cohort_drafts --sample 20 --save

    # hand-pick specific leads
    python manage.py preview_cohort_drafts --lead 42 --lead 87 --org NP-000123
"""
from __future__ import annotations

import sys

from django.core.management.base import BaseCommand

DEFAULT_CAMPAIGN = "Anansi Atlas — Founding Cohort"
# The agent prompt asks for the sender's name; the real agent takes it off the
# LinkedIn session profile, which this preview has no reason to open.
SELF_NAME = "Marcus Scott"



def _angle_menu() -> str:
    """The angle taxonomy, grouped by value family, for the prompt.

    Built from the model's own TextChoices so the prompt cannot drift from what the
    database will accept — adding an angle in one place adds it in both.
    """
    from collections import defaultdict

    from openoutreach.signals.models import ANGLE_FAMILY, OutreachAngle

    by_family: dict[str, list[str]] = defaultdict(list)
    for value, family in ANGLE_FAMILY.items():
        by_family[family].append(value)

    lines = [
        "## Classify your own argument — required",
        "",
        "Along with the email, return `primary_angle`: the ONE reason this reader might "
        "care, chosen from the list below. This is the reason, not the source — 'why they "
        "should care', never 'which database it came from'.",
        "",
        "Also return `angle_detail`: the concrete argument in a few words "
        "(e.g. 'CINS/FINS contract through 2026-06-30', 'county-provided technical "
        "assistance program'). Leave it empty if the angle is category-level with no "
        "specific behind it — do not invent one to fill the field.",
        "",
        "And `personalization`: 'personalized' only if a verified fact about THIS reader "
        "materially changes the reasoning; otherwise 'category_relevant'. Category-relevant "
        "is a legitimate email. Claiming personalized when the profile is thin is not.",
        "",
        "Atlas surfaces funding, partnerships, government pathways, free and low-cost "
        "resources, technical assistance and readiness. Do not default to a funding angle "
        "because funding is the most familiar — pick the reason the evidence best supports.",
        "",
    ]
    for family in ("funding", "partnership", "resource", "readiness"):
        values = sorted(by_family.get(family, []))
        lines.append(f"**{family}:** " + ", ".join(f"`{v}`" for v in values))
    lines.append("")
    lines.append(f"If none fit, use `{OutreachAngle.CATEGORY_MECHANISM}`. "
                 f"Use `{OutreachAngle.UNCLASSIFIED}` only if you genuinely cannot classify it.")
    return "\n".join(lines)


def _lead_facts(lead) -> list[str]:
    """Real, verified facts about a SalesLead — nothing inferred, nothing invented."""
    facts = []
    if lead.name:
        facts.append(f"Contact: {lead.name}" + (f", {lead.role}" if lead.role else ""))
    if lead.organization:
        facts.append(f"Organization: {lead.organization}")
    if lead.focus_area:
        facts.append(f"Focus area: {lead.focus_area}")
    if lead.region:
        facts.append(f"Region: {lead.region}")
    if lead.why_fit:
        facts.append(f"Why they're a fit: {lead.why_fit}")
    if lead.notes:
        facts.append(f"Notes: {lead.notes}")
    return facts


def _org_facts(org) -> list[str]:
    """Real, verified facts about a FloridaOrg from the IRS/enrichment data."""
    facts = [f"Organization: {org.name}"]
    if org.principal_officer:
        facts.append(f"Principal officer: {org.principal_officer}")
    where = ", ".join(p for p in (org.city, org.county and f"{org.county} County") if p)
    if where:
        facts.append(f"Location: {where}, FL")
    if org.ntee_sector:
        facts.append(f"Sector (IRS NTEE): {org.ntee_sector}")
    if org.website:
        facts.append(f"Website: {org.website}")
    if org.income_amount:
        facts.append(f"Annual income (IRS filing): ${org.income_amount:,}")
    return facts


class Command(BaseCommand):
    help = "Generate and print opener drafts for a few real orgs, to validate voice before automating."

    def add_arguments(self, parser):
        parser.add_argument("--lead", action="append", type=int, default=[],
                            help="SalesLead id to draft for. Repeatable.")
        parser.add_argument("--org", action="append", default=[],
                            help="FloridaOrg record_id (e.g. NP-000123) to draft for. Repeatable.")
        parser.add_argument("--sample", type=int, default=5,
                            help="If no --lead/--org given, draft for this many cold leads that have an email (default 5).")
        parser.add_argument("--campaign", default=DEFAULT_CAMPAIGN,
                            help=f"Campaign whose docs drive the prompt (default: {DEFAULT_CAMPAIGN!r}).")
        parser.add_argument("--prompt-only", action="store_true",
                            help="Print the assembled system prompt and exit. No API key needed, no model called.")
        parser.add_argument("--save", action="store_true",
                            help="Write each draft onto its SalesLead (subject_line + outreach_draft) so it "
                                 "appears in the operator cockpit for review. Still sends nothing.")
        parser.add_argument("--followup", action="store_true",
                            help="Write a SECOND touch for leads already emailed once with no reply. The "
                                 "draft acknowledges the earlier note instead of re-introducing Marcus. "
                                 "With --save, the original sent message is archived into notes first.")
        parser.add_argument("--redraft", action="store_true",
                            help="Include leads that already have a draft. Default skips them so batches advance.")

    def handle(self, *args, **options):
        from openoutreach.core.models import Campaign
        from openoutreach.signals.models import FloridaOrg, SalesLead

        campaign = Campaign.objects.filter(name=options["campaign"]).first()
        if campaign is None:
            self.stderr.write(self.style.ERROR(
                f"Campaign {options['campaign']!r} not found. "
                "Run `python manage.py seed_atlas_cohort_campaign` first."
            ))
            sys.exit(1)
        if not campaign.product_docs or not campaign.campaign_objective:
            self.stderr.write(self.style.ERROR(
                f"Campaign #{campaign.pk} has empty product_docs or campaign_objective — "
                "the prompt would have no voice in it. Re-run seed_atlas_cohort_campaign."
            ))
            sys.exit(1)

        # (label, facts, lead_or_None) — the lead is what --save writes back to.
        targets: list[tuple[str, list[str], object]] = []

        for lead_id in options["lead"]:
            lead = SalesLead.objects.filter(pk=lead_id).first()
            if lead is None:
                self.stderr.write(self.style.WARNING(f"SalesLead {lead_id} not found — skipped."))
                continue
            targets.append((f"SalesLead #{lead.pk} · {lead.organization or lead.name}", _lead_facts(lead), lead))

        for record_id in options["org"]:
            org = FloridaOrg.objects.filter(record_id=record_id).first()
            if org is None:
                self.stderr.write(self.style.WARNING(f"FloridaOrg {record_id!r} not found — skipped."))
                continue
            # A FloridaOrg is prospect universe, not a lead — promote it first if you want to save.
            targets.append((f"FloridaOrg {org.record_id} · {org.name}", _org_facts(org), None))

        if not targets:
            sample = (
                SalesLead.objects
                .filter(list_segment=SalesLead.Segment.COLD_FLORIDA_CRM)
                .exclude(email="")
                # Never draft for a lead the operator has retired. Passed means a
                # deliberate "not this one" — drafting it again wastes a call and
                # risks it reaching the send queue by way of the cockpit.
                .exclude(status=SalesLead.Status.PASSED)
            )
            if not options["redraft"]:
                # Skip anything already drafted so consecutive batches advance
                # through the list instead of re-drafting the same first N.
                sample = sample.filter(outreach_draft="")
            for lead in sample.order_by("pk")[: options["sample"]]:
                targets.append((f"SalesLead #{lead.pk} · {lead.organization or lead.name}", _lead_facts(lead), lead))

        if not targets:
            self.stderr.write(self.style.ERROR(
                "No targets. Pass --lead/--org, or check that undrafted cold leads with emails exist "
                "(every one may already have a draft — use --redraft to include them)."
            ))
            sys.exit(1)

        from openoutreach.core.agents.prompt import render

        FOLLOWUP_NOTE = (
            "SECOND TOUCH — a follow-up, not a first email.\n\n"
            "THE FIRST SENTENCE MUST BEGIN BY REFERRING TO THE EARLIER EMAIL. One short clause, "
            "then straight into the substance. Use one of these openings verbatim or close to it:\n"
            "    'I wrote a while back about ...'\n"
            "    'Following up on my note about ...'\n"
            "    'I sent a note some weeks ago about ...'\n\n"
            "They already know who Marcus is — he introduced himself in that first email — so "
            "'I'm Marcus Scott' or 'I'm reaching out because' is the wrong opening here; it tells "
            "the reader he has forgotten writing to them.\n\n"
            "Then give them ONE thing the first email didn't: the 80-second film, or the state/local "
            "gap stated plainly. Shorter than the first email, not longer — five or six sentences. "
            # "Close the same way: the site, or 30 minutes" produced "you can explore it at
            # anansiatlas.com" in four of ten drafts — the soft third CTA rule 7 bans. This note
            # is appended LAST, so it outranked the rule. Say what the two options actually are.
            "Close on the two real options and nothing else: joining the founding group, or 30 "
            "minutes. Never invite them to browse, explore, or take a look at the site — that is a "
            "third option, it is the easiest one, so it is the one they take instead of either "
            "real one. No guilt, no 'just checking in', no 'bumping this to the top of your "
            # "a one-line no is a perfectly good answer" used to live here, and the
            # house standard now bans it as a tic — it appeared in most of a batch and
            # stopped reading as sincerity. A note appended last would have overruled
            # the standard, which is this system's recurring failure.
            "inbox'. Do not append reassurance out of habit; end on the two options.\n\n"
            # Two failures seen in the last batch, both from the model reaching for email
            # conventions that don't apply to a stranger's second cold email.
            "NEVER prefix the subject with 'Re:'. There is no thread to reply to and it fakes one — "
            "a deceptive subject header, which is both a compliance violation and the fastest way "
            "to make a careful reader distrust everything under it. Write a plain subject.\n\n"
            "NEVER offer to 'pass this along to someone else at the organization'. Marcus does not "
            "know anyone else there — that is the recipient's introduction to make, not his. If "
            "they are the wrong person, the right line invites THEM to forward it."
        )

        ANGLE_MENU = _angle_menu()

        def prior_angle_block(lead) -> str:
            """Tell a follow-up what the opener already argued, if anything did.

            Structured, not prose: the previous body is in the record too, but asking a
            model to infer "have I already made this argument?" from prose is exactly the
            judgement call that produced ten paraphrases of one idea. A stored angle makes
            it a lookup.
            """
            if lead is None:
                return ""
            from openoutreach.signals.models import OutreachMessage, angle_family
            prev = OutreachMessage.last_for(lead, sent_only=True) or OutreachMessage.last_for(lead)
            if prev is None or not prev.primary_angle:
                # No record of the opener's angle — say so rather than inventing one.
                return ("\n\n## The previous touch\n"
                        "No angle was recorded for the earlier email, so you cannot know what it "
                        "argued. Pick the strongest angle the profile supports and do not attempt "
                        "to reference the earlier message's content.")
            detail = f" — {prev.angle_detail}" if prev.angle_detail else ""
            return (
                "\n\n## The previous touch — DO NOT REPEAT ITS ARGUMENT\n"
                f"The earlier email to this reader argued: **{prev.primary_angle}**"
                f" (value family: {angle_family(prev.primary_angle)}){detail}.\n\n"
                "They did not reply to that argument. Repeating it in different words is the "
                "single most common way a follow-up wastes its one remaining chance.\n\n"
                "**Choose a different primary_angle**, and prefer one from a different value "
                "family — funding, partnership, resource, readiness — because a shift between "
                "families is a materially different reason to care, while two funding angles is "
                "a small move. County funding → free technical assistance is a real change; "
                "county funding → state funding is barely one.\n\n"
                "Reuse the same angle ONLY if the profile carries genuinely new verified "
                "information that materially changes it. Rewording is not new information."
            )

        def build_prompt(facts: list[str], lead=None) -> str:
            prompt = render(
                "email_opener.j2",
                self_name=SELF_NAME,
                product_docs=campaign.product_docs,
                campaign_objective=campaign.campaign_objective,
                booking_link=campaign.booking_link or "",
                profile_summary="\n".join(f"- {f}" for f in facts) or "(none yet)",
                # SalesLead carries no scraped firmographics; the section collapses.
                company_intel="",
            )
            prompt += "\n\n" + ANGLE_MENU
            if options["followup"]:
                # email_opener.j2 opens by asserting "writing a first cold outreach
                # email ... You have never spoken before." A follow-up directive
                # buried in the facts list loses to that every time — it reads as
                # trivia about the recipient while the intro reads as identity. So
                # rewrite the claim at source, and repeat the instruction last,
                # where it isn't competing with anything.
                prompt = prompt.replace(
                    "writing a first cold outreach email to a lead you found through "
                    "professional research. You have never spoken before.",
                    "writing a FOLLOW-UP email to someone you already emailed once, weeks ago, "
                    "who did not reply. You have written to this person before.",
                )
                prompt += "\n\n## This email is a follow-up — read this last\n" + FOLLOWUP_NOTE
                prompt += prior_angle_block(lead)
            return prompt

        if options["prompt_only"]:
            label, facts, lead = targets[0]
            self.stdout.write(self.style.MIGRATE_HEADING(f"System prompt for: {label}\n"))
            # Pass the lead, not just its facts — otherwise the prior-angle block
            # renders empty here while appearing in the real run, and --prompt-only
            # stops being a preview of what the model actually receives.
            self.stdout.write(build_prompt(facts, lead))
            self.stdout.write(self.style.SUCCESS(
                f"\n\n({len(targets)} target(s) selected; showing the prompt for the first. "
                "Drop --prompt-only to generate drafts.)"
            ))
            return

        from pydantic_ai import Agent

        from openoutreach.core.agents.email_opener import EmailDraft
        from openoutreach.core.llm import get_llm_model, run_agent_sync

        try:
            model = get_llm_model()
        except Exception as exc:  # noqa: BLE001 — surface config problems plainly
            self.stderr.write(self.style.ERROR(
                f"Could not build the LLM model ({exc}). Set the provider + API key in "
                "SiteConfig (/admin/) — the same key that gates Layer-2 discovery. "
                "Use --prompt-only to inspect the prompt without one."
            ))
            sys.exit(1)

        saved = 0
        for label, facts, lead in targets:
            self.stdout.write(self.style.MIGRATE_HEADING(f"\n=== {label}"))
            if not facts:
                self.stdout.write(self.style.WARNING("  (no facts on file — the draft will be generic by necessity)"))
            agent = Agent(model, output_type=EmailDraft, model_settings={"temperature": 0.7, "timeout": 60})
            try:
                draft = run_agent_sync(agent.run(build_prompt(facts, lead))).output
            except Exception as exc:  # noqa: BLE001 — one bad draft shouldn't kill the batch
                self.stderr.write(self.style.ERROR(f"  draft failed: {exc}"))
                continue
            self.stdout.write(f"\nSubject: {draft.subject}\n")
            self.stdout.write(draft.body)
            if draft.primary_angle:
                from openoutreach.signals.models import angle_family
                detail = f" · {draft.angle_detail}" if draft.angle_detail else ""
                self.stdout.write(self.style.HTTP_INFO(
                    f"\n  [angle: {draft.primary_angle} ({angle_family(draft.primary_angle)})"
                    f"{detail} · {draft.personalization or 'unclassified'}]"))

            if options["save"]:
                if lead is None:
                    self.stdout.write(self.style.WARNING(
                        "  (not saved — a FloridaOrg is prospect universe, not a lead. Promote it to the "
                        "pipeline first, then draft against the resulting SalesLead.)"
                    ))
                else:
                    from openoutreach.signals.models import OutreachMessage

                    # The draft on a sent lead IS the record of what went out, and it
                    # used to be preserved by appending it into `notes` — which then fed
                    # back into the prompt as a "fact about the lead", sharing one field
                    # with the researched profile and the operator's own notes. The
                    # OutreachMessage row is that archive now, so notes is left alone.
                    prior = OutreachMessage.last_for(lead)
                    genre = (OutreachMessage.Genre.COLD_FOLLOWUP if options["followup"]
                             else OutreachMessage.Genre.COLD_OPENER)
                    OutreachMessage.objects.create(
                        lead=lead,
                        campaign=campaign,
                        genre=genre,
                        sequence_position=(prior.sequence_position + 1) if prior else 1,
                        subject=draft.subject.strip()[:300],
                        body=draft.body,
                        primary_angle=(draft.primary_angle or "").strip().lower()[:40],
                        angle_detail=(draft.angle_detail or "").strip()[:300],
                        personalization=(draft.personalization or "").strip().lower()[:20],
                        status=OutreachMessage.Status.DRAFTED,
                    )
                    lead.subject_line = draft.subject.strip()[:300]
                    lead.outreach_draft = draft.body
                    lead.save(update_fields=["subject_line", "outreach_draft"])
                    saved += 1
            self.stdout.write("")

        if options["save"]:
            self.stdout.write(self.style.SUCCESS(
                f"\n{saved} draft(s) saved to their leads — they're now in the operator cockpit for review. "
                "Nothing has been sent: the cockpit sends only when you click send."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                "\nRead these against the voice guide before automating anything upstream. "
                "Nothing was written to the database and nothing is queued to send. "
                "Add --save to put a batch into the cockpit for review."
            ))
