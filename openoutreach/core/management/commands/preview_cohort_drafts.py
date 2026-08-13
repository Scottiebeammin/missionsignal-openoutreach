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

import re
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


FINAL_CHECKS = """\
## Before you return the draft — check these four, in order

Every rule this system has broken was correct and upstream of something that
contradicted it. These are the four that keep breaking, placed last on purpose.

1. **The close is exactly two options: the founding group, or 30 minutes.** Delete any
   invitation to "explore", "take a look at", "check out" or "see" the site. That is a
   third option, it is the easiest one on the page, and it is therefore the one they
   take instead of either real one — while implying results already exist for an
   organization that has no workspace.
2. **No name in the greeting** unless the address is one person's mailbox AND the
   profile confirms they currently hold the role. If the profile mentions a
   succession, an interim or a departure, use no name.
3. **You did not look anything up.** Delete "I saw", "I noticed", "I came across",
   "I was reading". State the fact plainly instead — the fact is allowed, narrating
   having found it is not.
4. **Every specific traces to the profile.** Any programme, date, figure, funder or
   role that is not in it comes out.
"""

def normalize_angle(raw: str) -> tuple[str, str]:
    """Return (angle, warning). An unrecognised value is recorded as unclassified.

    The model returned "funding" once — a value-family name, not an angle. Stored
    verbatim it fails the family lookup and shows as "(unknown)", which silently
    removes that message from the follow-up comparison: `angle_is_materially_new`
    can only tell a repeat from a change if both sides are real angles. Better to
    record honestly that it was not classified, and say so.
    """
    from openoutreach.signals.models import ANGLE_FAMILY, OutreachAngle

    value = (raw or "").strip().lower()
    if not value:
        return "", ""
    if value in ANGLE_FAMILY or value == OutreachAngle.UNCLASSIFIED:
        return value, ""
    return (OutreachAngle.UNCLASSIFIED,
            f"model returned {raw!r}, which is not an angle "
            f"(a value family is not an angle) — recorded as unclassified")


def _lead_facts(lead) -> list[str]:
    """Verified facts about a SalesLead — nothing inferred, nothing invented.

    This list is handed to the writer as recipient evidence, so only fields approved
    for that reach it. Three that deliberately do NOT:

    * ``notes`` — the legacy mixed field. It held researched profile, archived prior
      emails and operator commentary at once, and was passed through here under a
      "Notes:" heading, which let "probably short-staffed" come back as "with your
      staffing challenges". Nothing here can distinguish which sentences in an old
      blob were research, so none of it is trusted.
    * ``operator_notes`` — workflow commentary by construction. "Call Marcus first"
      is an instruction, not a fact about the organization.
    * ``relationship_context`` — real, but a different authority level. It goes to the
      writer through ``_relationship_block`` under its own heading instead.
    """
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
    if lead.research_profile:
        facts.append(f"Researched profile: {lead.research_profile}")
    return facts


#: Local-parts that are a desk, not a person. A greeting by first name to one of
#: these is wrong twice: the named person may not read it, and the name may be stale.
_SHARED_LOCALPARTS = frozenset({
    "info", "hello", "contact", "admin", "office", "mail", "general", "inquiries",
    "information", "administration", "frontdesk", "frontoffice", "reception", "support",
    "help", "team", "staff", "main", "service", "services", "school", "secretary",
})
#: A function rather than an inbox — a person may read it, but not necessarily the
#: one named on the lead.
_ROLE_LOCALPARTS = frozenset({
    "marketing", "development", "recovery", "giving", "donate", "volunteer", "grants",
    "outreach", "media", "press", "hr", "jobs", "enroll", "admissions", "registrar",
    "principal", "director", "intake", "business", "askjp",
})


def address_kind(email: str) -> str:
    """'personal', 'role' or 'shared' — who is actually behind this address.

    Deterministic, because the alternative is the model inferring it from a name that
    may be years out of date. Eighteen of the twenty cold leads are shared inboxes.
    """
    local = re.sub(r"[^a-z]", "", (email or "").split("@")[0].lower())
    if not local:
        return "shared"
    if local in _SHARED_LOCALPARTS:
        return "shared"
    if local in _ROLE_LOCALPARTS or any(r in local for r in _ROLE_LOCALPARTS):
        return "role"
    return "personal"


def _address_note(lead) -> str:
    """Tell the writer what kind of address this is, and how to open because of it."""
    if lead is None or not getattr(lead, "email", ""):
        return ""
    kind = address_kind(lead.email)
    if kind == "personal":
        return (
            "\n\n## The address\n"
            f"`{lead.email}` looks like one person's mailbox. A first-name greeting is "
            "appropriate IF the profile confirms who currently holds the role — see the "
            "greeting rule. If it does not, greet without a name."
        )
    what = "a shared inbox" if kind == "shared" else "a role or department address"
    return (
        "\n\n## The address — DO NOT GREET BY NAME\n"
        f"`{lead.email}` is {what}, not one person's mailbox. Whoever opens it is often "
        "an administrator rather than the leader, so:\n"
        "- **Open without a personal name.** No 'Dana —', no 'Hi Dana'. Start with the "
        "substance, or a plain 'Hello'.\n"
        "- **Write so it survives being forwarded.** The first reader may not be the "
        "decision-maker; the email has to make sense to a second reader with no context, "
        "and give the first one an obvious reason to pass it on.\n"
        "- The subject line carries more weight than usual, because the person who "
        "decides whether to forward it may read nothing else."
    )


def research_gap(lead) -> str:
    """Why this lead's research looks stranded rather than genuinely absent, or "".

    There are two ways a lead can reach the writer with no researched profile, and
    they must not be treated the same:

    * **Genuinely thin** — nothing was ever researched. That is fine. The writing
      standard degrades to a category-relevant email, which is a legitimate email.
    * **Stranded** — research exists, but in the legacy ``notes`` field that the
      writer no longer trusts. This looks identical to "thin" from inside the
      prompt, and it is not: it is a deployment mistake, and it silently costs the
      draft everything that was learned about the organization.

    The second case is what this catches. It happens on exactly one boundary —
    deploying the research/notes split before re-running the command that populates
    ``research_profile`` — and on that boundary it would hit every lead at once.
    """
    if lead is None or getattr(lead, "research_profile", ""):
        return ""
    if (getattr(lead, "notes", "") or "").strip():
        return ("has legacy notes but an empty research_profile — the research is probably "
                "stranded in the old field. Re-run seed_lead_intel before drafting")
    return ""


def _relationship_block(lead) -> str:
    """Approved relationship history, kept at arm's length from researched fact.

    Warm outreach needs "Marcus worked with her at Aeras" — but that is a fact about
    Marcus, not about the organization, and it must not be quotable as though the
    research turned it up. Its own heading, its own authority level.
    """
    if lead is None or not getattr(lead, "relationship_context", ""):
        return ""
    return (
        "\n\n## Relationship context — NOT researched fact\n"
        f"{lead.relationship_context.strip()}\n\n"
        "This is genuine shared history, and it may inform the tone and the reason for "
        "writing now. It is not a finding about the organization: do not present it as "
        "something the research surfaced, and do not extend it into claims it does not "
        "make."
    )


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
        parser.add_argument("--allow-missing-research", action="store_true",
                            help="Draft even when a lead's research looks stranded in the legacy "
                                 "notes field. Held by default: a stranded profile is "
                                 "indistinguishable from no profile once inside the prompt, and "
                                 "silently costs the draft everything known about the org.")
        parser.add_argument("--include-held", action="store_true",
                            help="Draft even for leads held for review or disqualified. For "
                                 "inspecting what would be written — the send path still refuses "
                                 "them, so this cannot put mail in front of anyone.")
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
            # Defence in depth. The authoritative gate is in send_outreach_email, but
            # spending a model call on a lead that can never be sent is waste, and a
            # draft sitting in the cockpit for a disqualified org invites someone to
            # wonder why it won't send.
            block = lead.cold_outreach_block()
            if block:
                self.stderr.write(self.style.WARNING(
                    f"SalesLead #{lead.pk} ({lead.organization or lead.name}) is {block} — skipped. "
                    f"Pass --include-held to draft it anyway."))
                if not options["include_held"]:
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
                # Never draft for a lead that cannot be sent to. `passed` is the
                # operator's manual retirement; `disposition` is the research layer's
                # verdict. Both belong here — but note this filter only ever guarded
                # the sample path, so the real gate is in send_outreach_email.
                .exclude(status=SalesLead.Status.PASSED)
                .filter(disposition=SalesLead.DISPOSITION_ELIGIBLE)
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
            prompt += _address_note(lead)
            prompt += _relationship_block(lead)
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
            # Last position, deliberately: this is the only slot that has reliably
            # beaten a contradicting rule elsewhere in the prompt.
            prompt += "\n\n" + FINAL_CHECKS
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
        held_for_research = 0
        for label, facts, lead in targets:
            self.stdout.write(self.style.MIGRATE_HEADING(f"\n=== {label}"))
            gap = research_gap(lead)
            if gap:
                self.stderr.write(self.style.ERROR(f"  HELD: {gap}."))
                if not options["allow_missing_research"]:
                    held_for_research += 1
                    continue
                self.stderr.write(self.style.WARNING(
                    "  --allow-missing-research given; drafting without it anyway."))
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
            angle, angle_warning = normalize_angle(draft.primary_angle)
            if angle_warning:
                self.stderr.write(self.style.WARNING(f"  {angle_warning}"))
            if angle:
                from openoutreach.signals.models import angle_family
                detail = f" · {draft.angle_detail}" if draft.angle_detail else ""
                self.stdout.write(self.style.HTTP_INFO(
                    f"\n  [angle: {angle} ({angle_family(angle)})"
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
                        primary_angle=angle[:40],
                        angle_detail=(draft.angle_detail or "").strip()[:300],
                        personalization=(draft.personalization or "").strip().lower()[:20],
                        status=OutreachMessage.Status.DRAFTED,
                    )
                    lead.subject_line = draft.subject.strip()[:300]
                    lead.outreach_draft = draft.body
                    lead.save(update_fields=["subject_line", "outreach_draft"])
                    saved += 1
            self.stdout.write("")

        if held_for_research:
            self.stderr.write(self.style.ERROR(
                f"\n{held_for_research} lead(s) held: research is stranded in legacy notes. "
                "Run `python manage.py check_research_readiness` to see which, then re-run "
                "seed_lead_intel. Nothing was drafted for them."))
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
