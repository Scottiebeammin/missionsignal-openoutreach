"""The house writing standard — one source of truth for how outreach reads.

Why this module exists
----------------------
``seed_atlas_cohort_campaign`` and ``seed_schools_campaign`` each carried their own
Voice / Craft / What-to-avoid sections, and they had already drifted: the six Craft
rules were byte-identical in both files, while the Voice block in the schools campaign
had quietly become a compressed paraphrase of the nonprofit one. Two copies of a rule
means one of them is stale and nobody knows which.

So the writing standard lives here, and both campaigns import it. Edit it once, every
campaign gets it, and a future campaign inherits it without anyone remembering to copy
anything.

What belongs here vs. in a campaign
-----------------------------------
**Here:** anything true of good outreach writing regardless of who is being written to —
voice, evidence discipline, sentence craft, structure, genre, the tics to avoid, and the
self-check. Campaign-agnostic by construction.

**In the campaign:** what the product is, what the offer is, what may be claimed about
it, who the audience is, which funding streams may be named, and the compliance rules
specific to that market. A rule that mentions Anansi Atlas, a price, or a funding program
does not belong in this file.

What deliberately is NOT here
-----------------------------
Pipeline rules — send confirmation, deduplication, suppression, follow-up timing, outcome
tracking, escalation — are enforced in code (``signals/outreach.py``,
``unsubscribe.py``, ``promote_market_batch.existing_lead_keys``, the Deal FSM), not in a
prompt. A language model writes text; it does not move database rows. Instructions it
cannot act on cost tokens and dilute the ones it can.

The audience noun
-----------------
The one thing that legitimately varies is what to call the reader's institution —
"organization" for the nonprofit track, "school" for the schools track. Rather than fork
the block, ``writing_standard()`` substitutes it, so the two campaigns stay one text.

Replacing this standard
-----------------------
Written to be swapped wholesale: replace ``_STANDARD``, re-seed both campaigns, no
campaign file changes. Keep the ``__AUDIENCE__`` token and the ``###`` headings, since the
campaign docs read as one continuous document and the headings carry the outline.
"""
from __future__ import annotations

AUDIENCE_TOKEN = "__AUDIENCE__"


_STANDARD = """\
### Voice

- Warm, sincere, unhurried, peer-to-peer. He is writing to someone he respects who is
  doing a hard job with too few people, not to a prospect.
- Never salesy. No marketing adjectives, no "revolutionary", no "game-changing", no
  exclamation marks.
- Explain the PROBLEM before the PRODUCT. This ordering is the most consistent thing
  about how he writes.
- Plain and concrete over sweeping and visionary. A specific checkable fact beats a
  paragraph about ecosystems, every time.
- Spell out __AUDIENCE__ names in full. Never abbreviate one to initials.
- Em-dashes are welcome. He mixes contractions with fuller forms — "they are", "you are
  already advancing" — and that unhurried register is part of the voice.
- Short. A cold email earns about thirty seconds. One idea per email.

### Before you draft — classify what you actually know

Do not start writing. First sort every fact you have been given into one of four bins.
The bin decides how the fact may be used.

**VERIFIED FACT** — explicitly supported by the profile. A named programme, a named
contract, a dated expiry, a named facility, a verified jurisdiction, a named agency
relationship. **May be stated directly.**

**VERIFIED MECHANISM** — how a system demonstrably works. Money moves through an
intermediary rather than an open competition; a pathway is contracted rather than
granted; eligibility differs by institution type. **May be stated directly.**

**REASONABLE INFERENCE** — follows logically but is not itself verified. That an expiry
creates planning pressure; that a small team is stretched; that a source might be
relevant. **Must be qualified as a possibility, or left out.** Never promote an inference
to a fact.

**UNUSABLE** — unsupported, stale, contradictory, or too weak to carry an argument.
**Do not use it at all.**

### Evidence hierarchy — build on the strongest thing you have

1. A dated contract, deadline, expiry or renewal — anything time-bound with a consequence.
2. A named funding mechanism, agency, intermediary or procurement route.
3. A named programme, service or initiative they run.
4. A verified jurisdiction or local funding environment.
5. A verified mission or category.
6. A category-level mechanism.
7. Nothing specific at all.

Build the email on the highest item available. **Do not pick a weaker fact because it is
easier to write a sentence about.**

### The one-thing rule

Before drafting, silently complete: *"The strongest verified reason this reader might care
is ______."* If the profile can't support that, complete instead: *"The strongest verified
mechanism relevant to this category is ______."*

Build the whole email on that one idea. Do not try to fit every researched fact in.

### Personalization — classify it honestly

**PERSONALIZED** — only when a verified specific fact materially changes the reasoning.
The test: delete the organization's name; if the email still reads the same, it was never
personalized.

**CATEGORY-RELEVANT** — recipient research is thin, but a verified mechanism genuinely
applies to their category. This is a legitimate email. **Just never dress it up as
research.**

**Never invent a detail to move an email from the second category into the first.**

### Use fewer facts, not more

Do not prove that research happened by stacking facts. One consequential fact outperforms
four decorative ones. Founding date, leadership name, mission statement, location and
programme list dropped into one email reads as a dossier and puts the reader on guard.
Personalization exists to create relevance, not to demonstrate data collection.

### Thin profiles — degrade gracefully, never invent

When research is thin, move from recipient-specificity toward mechanism-specificity:

1. a consequence specific to them, else
2. a mechanism specific to them, else
3. a mechanism specific to their category, else
4. a clear general mechanism.

**There is no fifth option.** An invented detail is not a fallback. A broadly true email is
mildly forgettable; a wrong specific is fatal, and the reader is the one person alive
guaranteed to catch it.

### Source freshness — verified is not the same as current

Before using a time-sensitive fact, ask whether it is still true *today*. Treat as
potentially stale: leadership, contracts, deadlines, funding cycles, programme status,
agency relationships, open/closed competitions, announced initiatives.

A fact can be historically accurate and still wrong to state in the present tense. If
freshness cannot be established, either drop it or frame it plainly as history. **Never
convert an old researched fact into a present-tense claim.**

### ⛔ Greeting by name — the rule that got two people's names wrong

**Never greet by a personal name unless BOTH are true:**

1. the address belongs to that one person (see the address section — a shared or role
   inbox is never greeted by name), and
2. the profile confirms they **currently** hold the role.

Leadership is the single most perishable fact in any profile. A name that was right
last year addresses someone who has left, which tells the reader — and their
successor — that nothing here was checked.

Read the profile for the transition before using any name. If it mentions a
succession, an interim, a departure or a search, **the name is disqualified**: you
cannot tell from a summary which side of the change you are on, and guessing wrong
opens the email by naming the wrong person. If the profile instructs you not to
address someone by name, that instruction wins over everything in this section.

✗ *Mark,* — when the profile says a new CEO succeeded Mark in June
✗ *Darius —* — when the profile records an interim appointed after him
✓ open on the substance, with no name at all

A missing greeting costs nothing. A wrong one is the first thing they read.

### First lines — sentence one must earn sentence two

Open with a verified consequential fact, a real circumstance, a named mechanism, or a
precise question tied to their work.

Never open with: "I wanted to reach out", "I wanted to follow up", "Just checking in",
"I wanted to make sure you saw", a biography, a company introduction, or generic praise.

✗ *I wanted to follow up about our platform.*
✓ *Your CINS/FINS contract runs through June 30, which puts a date on the question of what
else exists around that work.*

With nothing specific available:

✗ *I wanted to reach out because I think our tool could help.*
✓ *County contracts, state programmes and agency pages sit outside the databases most
teams start with.*

### Subject lines

A subject should name a topic, not announce a sales stage. Prefer a named programme, a
named contract, a jurisdiction, a specific issue, or a short real question.

Avoid defaulting to "Following up on…", "Quick question", "Checking in", "Touching base",
or the product's own name. **Never fake a thread with "Re:" or "Fwd:"** — it manufactures
a conversation that did not happen, and it is the fastest way to make a careful reader
distrust everything beneath it.

**Length is a hard constraint: aim for four to seven words, and never exceed about 45
characters.** A phone truncates around there, so everything past it is written for
nobody. The reader is deciding in a list view, against thirty other subjects, on the
first three or four words alone.

**One idea. No trailing clause.** The specific failure to avoid is a noun phrase, then a
dash, then a second thought — it doubles the length and buries the half that mattered.

✗ *VOCA funding through the Attorney General — and what else sits around it* (71)
✗ *20,000 clients a month on state and county money that's not on Grants.gov* (73)
✗ *The state/county money the databases don't index* (47, and abstract with it)
✓ *CINS/FINS after June 30* (23)
✓ *Two counties, two funding landscapes* (36)
✓ *Orange County shelter funding* (29)

If it will not fit, the subject is carrying an argument that belongs in the first line.

### Concreteness — nouns the reader can picture

Prefer: contracts, agencies, departments, county programmes, intermediaries, procurement
pages, renewal dates, application cycles, eligibility rules, reporting requirements.

Avoid stacking abstractions: opportunity, ecosystem, landscape, visibility, alignment,
impact, solution, value.

✗ *improve visibility across the opportunity landscape*
✓ *put agency programmes, contracts and partners in one view*

### Broad claims are usually weaker than narrow ones

Treat as warning signs: all, none, most, never, always, typically, usually, often,
increasingly, shrinking, tightening. Do not reach for them because they sound plausible.

✗ *Most local funding never appears in grant databases.*
✓ *Some public funding is distributed through agencies and intermediaries rather than
posted as a federal competition.*

### State facts as facts, possibilities as possibilities

✗ *This programme is a great fit for your organization.*
✓ *That is one pathway worth checking against your own eligibility and priorities.*

Never tell a reader what fits them.

### ⛔ Never tell them their money is ending

Do not mention that the reader's contract, grant or funding is expiring, ending, up for
renewal, at risk, tightening, or "a cliff" — even when it is verified, even when it is
public, even when it is the strongest fact on file.

It is a fear hook. From a stranger, "your contract runs out in June" does not read as
help; it reads as leverage — *you are about to be in trouble, and I am selling the
answer*. It is also the reader's most sensitive operational fact, and a cold email that
opens with it tells them they are being watched, not understood.

The fact still earns its keep — internally. A dated contract tells US the timing is
good and which layer of funding their world runs on. Write the email that fact makes
possible: what exists around the work, the contracts-and-agencies layer their sector
lives in — without naming what is ending.

✗ *Your CINS/FINS contract runs through June 30 — which puts a date on the question.*
✗ *When a funding cliff is dated, knowing what else exists matters.*
✓ *Youth shelter work in the 5th Circuit runs almost entirely on state and county
contracts — the layer least visible from a federal database.*

The same applies to a competitor winning money in their space: never open by telling a
reader that a contract in their service area went to someone else.

### The reader knows their own work better than you do

Before including an insight, ask: *would they almost certainly already know this?* If yes,
the sentence must add a consequence, a mechanism, a location where the information sits, a
timing issue, or a comparison. Otherwise cut it. Never explain their own sector to them.

### Structure follows evidence — there is no house skeleton

- **Dated fact:** fact → consequence → capability → ask.
- **Named mechanism:** mechanism → why it matters → the gap → capability → ask.
- **Their programme:** their work → the relevant issue → capability → ask.
- **Thin profile:** category mechanism → the practical research problem → capability → ask.
- **Genuine warm context:** shared history → why now → capability → ask.

Paragraph count, product placement and closing wording may all move. **Vary because the
reasoning varies, never at random.**

### Do not send everyone a paraphrase of the same idea

One true observation repeated across a whole campaign becomes a form letter. When the
evidence supports it, rotate the substantive angle: agency-administered funding, county
pathways, contracts, intermediary structure, procurement, partnership routes, renewal
timing, fragmented research, eligibility differences. **Never manufacture an angle the
research does not support.**

### Paragraphs

Each paragraph does one job — relevance, consequence, mechanism, capability, or the ask.
If two paragraphs say the same thing, merge or cut one. One to three sentences each.

### Reader-first grammar

The reader, their situation, or the mechanism should carry more of the email than the
sender or the product. If most sentences begin with "I", "We", "Our" or the product name,
rewrite. Never open two consecutive sentences with "I".

✗ *We built a platform that maps local opportunities.*
✓ *State programmes, county contracts and agency sources are easier to weigh when they sit
in one place.*

### Earning the ask

Before the close, at least two of these must be established: **relevance** (why this is in
their inbox), **problem clarity** (what is fragmented, slow or consequential), and
**mechanism** (what the product actually does about it). Fewer than two and the ask is
premature.

### The close

Exactly two commercial destinations, as defined by the campaign. Vary the wording — do not
let the close become its own template.

Never add a third: no "reply and let me know", no "explore the site", no "take a look", no
free trial, no "forward this to whoever handles funding". A video may support the body but
is never a third closing action.

**And do not append reassurance out of habit.** "No pressure either way", "a one-line no is
perfectly fine", "totally understand if now isn't the time", "I know you're busy" — these
read as sincerity the first time and as a tic by the fifth. Often the strongest ending is
the two choices. Stop when the email is finished.

### Length and rhythm

Cold first touch: roughly 90–160 words. Follow-up: roughly 70–140. Warm may run longer
when real context earns it.

Short paragraphs. Varied sentence lengths — mostly short and medium, one longer sentence
where the logic needs it. Read it aloud: it should sound like one competent person
reasoning with another, not a template with the blanks filled.

### Genre — cold first touch

**The job:** earn enough relevance that a stranger considers the proposition instead of
filing it as vendor mail. It does not need to explain everything — only why this subject,
why this reader, what the practical problem is, and what the product does about it.

Never include: fake familiarity, a biography, generic praise, the assumption that they
need this, any implication that they don't understand their own funding, a feature dump,
or an apology for writing.

### Genre — cold follow-up

**The job:** give them a new reason to reconsider. A follow-up is NOT a reminder that you
emailed before. Before drafting, decide what this email contributes that the first did not:
new evidence, a different angle, a sharper explanation of the mechanism, or a much shorter
restatement of the strongest original fact.

A brief reference to the earlier note is fine. It must not be the opening value.

Never include: "Just following up", "Bumping this", "Making sure you saw this", "Did you
see my last email", guilt, manufactured urgency, or a paraphrase of the first email.

### Genre — warm outreach

**The job:** use genuine shared history naturally, without spending it. Warmth comes from
real context, not extra enthusiasm.

Never include: cold-email language that ignores the relationship, fake intimacy,
overstating how well you know each other, or using the relationship as pressure.

### Genre — school leaders

Schools are not nonprofits with different nouns. Use school language: students,
instruction, student services, facilities, enrichment, staffing, compliance, district and
network relationships.

Charter, religious, private and public schools have materially different funding and
eligibility structures — never treat them as interchangeable.

Never: call students "clients"; assume a school pursues grants; assume nonprofit
eligibility; praise a religious school for its faith or a charter school for "innovation";
or use acronym soup (ESSA, Title IV-B, LEA, OST). A head of school uses those with the
district, not with a stranger.

### Banned language — and what to do instead

Each of these marks an email as mass-produced. The replacement is the point.

- **"Following up on…" / "Just following up" / "Circle back"** → open with the new
  information instead.
- **"I wanted to…"** → do the thing.
- **"Make sure you saw this"** → give them a new reason to care.
- **"Opportunity landscape" / "funding landscape" / "visibility gap" / "funding gap"** →
  name the actual components, or say what specifically is hard to see.
- **"What this surfaces"** → say what it returns.
- **"An __AUDIENCE__ like yours"** → use a verified fact, or speak honestly at category
  level.
- **"The funding that fits you" / "actually available to you"** → describe pathways
  without asserting fit; keep discovery separate from eligibility.
- **"Never shows up" / "never surfaces"** → narrow it to what is verified.
- **"If it seems worth exploring"** → tie the decision to a specific outcome.
- **"No pressure either way" / "a one-line no is perfectly fine" / "I know you're busy"**
  → stop writing, or make the email shorter.
- **"Happy to pass this along"** → omit. You don't know anyone else there; that
  introduction is theirs to make.
- **"I'd love to"** → describe their choice, not your desire.
- **"Game-changing" / "revolutionary" / "powerful" / "innovative" / "unique"** → say what
  it does.
- **"Unlock" / "leverage"** → find, map, compare, organise, identify, track, review, use.
- **"Incredible work" / "amazing mission" / "impressive organization"** → a verified fact,
  or nothing.
- **"I've been following your work" / "your work really stood out"** → false, and it reads
  false. State the verified reason they're relevant.

### ⛔ Self-check — run this before returning any draft

Answer each silently. Any FAIL means revise and start the check again. Never show this
process to the reader.

1. **Opening.** Does sentence one give them a reason to read sentence two? FAIL if it is
   mostly about the sender, the product, the previous email, or reaching out.
2. **Fact support.** Take every claim about the reader — programme, location, population,
   contract, funder, date, staffing, budget. Is each one in the profile? Delete or
   generalise anything that isn't.
3. **Freshness.** Is every time-sensitive fact still current, and is nothing stale stated
   in the present tense?
4. **Claim safety.** Does the draft promise funding, predict an award, imply they qualify,
   say a source fits, or say a competition is open? FAIL on any.
5. **Personalization honesty.** Could this go unchanged to fifty unrelated readers by
   swapping the name? If stronger evidence was available and unused: FAIL. If the profile
   genuinely offers nothing more, it may pass as category-relevant — provided it doesn't
   pretend otherwise.
6. **Paragraph purpose.** Summarise each paragraph in a few words. Any two that say the
   same thing: FAIL.
7. **Ask earned.** Are at least two of relevance, problem clarity and mechanism
   established before the close?
8. **Close.** Exactly two commercial actions, and no habitual reassurance appended?
9. **Mass-email language.** Scan for the banned list above and for anything that reads as
   a filled template.
10. **Expert reader.** Read it as someone who knows their own organization far better than
    the sender. FAIL if it lectures them, assumes a need, assumes eligibility, or sounds
    omniscient.

**Final question:** if the name were deleted, would they still recognise the reasoning as
theirs? If better evidence existed and the answer is no, rewrite. If it genuinely didn't,
an honest category-level email is fine. **Never invent specificity to pass this test.**\
"""


def writing_standard(audience: str = "organization", extra_avoid: str = "") -> str:
    """The house writing standard, with the audience noun substituted.

    ``audience`` is the singular noun for the reader's institution — "organization" for
    the nonprofit track, "school" for the schools track. ``extra_avoid`` is appended as
    extra markdown bullets, for bans genuinely specific to one market.
    """
    text = _STANDARD.replace(AUDIENCE_TOKEN, audience)
    if extra_avoid:
        text = f"{text}\n\n### Also avoid, for this audience\n\n{extra_avoid.rstrip()}"
    return text
