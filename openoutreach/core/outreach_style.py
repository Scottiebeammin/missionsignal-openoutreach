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
voice, sentence craft, structure, the tics to avoid. Campaign-agnostic by construction.

**In the campaign:** what the product is, what the offer is, what may be claimed about
it, who the audience is, and the compliance rules specific to that market. A rule that
mentions Anansi Atlas, a price, or a funding program does not belong in this file.

The audience noun
-----------------
The one thing that legitimately varies is what to call the reader's institution —
"organization" for the nonprofit track, "school" for the schools track. Rather than fork
the block, ``writing_standard()`` substitutes it, so the two campaigns stay one text.

Replacing this standard
-----------------------
This is written to be swapped wholesale. When a better standard is authored, replace
``_STANDARD`` and both campaigns update on the next seed run — no campaign file changes.
Keep the ``__AUDIENCE__`` token and the section headings, since the campaign docs read as
one continuous document and the headings carry the outline.
"""
from __future__ import annotations

AUDIENCE_TOKEN = "__AUDIENCE__"


_STANDARD = """\
### Voice

- Warm, sincere, unhurried, peer-to-peer. He is talking to someone he respects who is
  doing a hard job with too few people, not to a prospect.
- Never salesy. Never hype. No marketing adjectives, no "revolutionary," no
  "game-changing," no exclamation marks.
- Explain the PROBLEM before the PRODUCT. The problem comes first; what we do about it
  comes second. This ordering is the single most consistent thing about how he writes.
- Plain and concrete over sweeping and visionary. A specific, checkable fact beats a
  paragraph about ecosystems, every time.
- Spell out __AUDIENCE__ names in full. Never abbreviate one to initials.
- Em-dashes are welcome. He mixes contractions with fuller forms — "they are," "you are
  already advancing" — and that unhurried register is part of the voice.
- Generous and respectful. Low pressure. A "no" is genuinely fine.
- Short. A cold email earns about thirty seconds. One idea per email — the long-form,
  richly-detailed version of this voice belongs in warm outreach to people he actually
  knows, not here.

### Craft — how to make the writing better, not just correct

These are the specific ways a draft goes flat. Each one has a fix.

**1. Explain the purpose, don't list the parts.** "Aligned funders, government pathways,
strategic partners, and a practical 30-day action plan" is a brochure — four nouns in a row
that the reader skims. Say what it *does for them*: they'll see opportunity around their
work that they couldn't see on their own. One clear idea beats four features.

**2. Vary the opening. Do not begin every email the same way.** A true sentence that opens
every message is still a form letter, and the people receiving these compare notes. Rotate
what comes first: the gap in where funding is listed, a plain question, the county, or the
credential. The credential can arrive in the second sentence just as well as the first.

**3. Cut vague praise.** "Doing work that matters," "the work you're building," "an
__AUDIENCE__ like yours." These are what a stranger says when they know nothing, and they
read that way. Either say something specific and true, or say nothing and get to the point —
an email with no compliment is more respectful than one with an empty compliment.

**4. Shorter. Aim for about 130 words.** Four paragraphs is too many for a first cold email.
Three short ones is the shape: the problem, what we do about it, the ask. If a sentence
isn't carrying the argument, delete it.

**5. Make the closing question specific enough to answer.** "What does your funding
landscape look like right now?" is a hard question to answer in an inbox. "Would it be
useful to see what this surfaces for [name]?" is answerable in one word.

**6. Never open two consecutive sentences with "I".** The reader cares about their own
__AUDIENCE__; the email should sound like it's about them, not about the sender.

**7. No fake threading.** Never prefix a subject with "Re:" or "Fwd:" on an email that is
not a reply. It manufactures a conversation that did not happen — a deceptive subject
header, and the fastest way to make a careful reader distrust everything beneath it.

**8. Don't offer to pass it along yourself.** "Happy to pass this along to someone else
there" is backwards: he doesn't know anyone else there. That introduction is the
recipient's to make. If they may be the wrong person, invite THEM to forward it.

### What to avoid — universal

- Opening with a paragraph about Marcus. Credibility comes from one clause, not a bio.
- Stacking every idea into the first email — the founder story, the problem, the product,
  the plan, the video, the ask. Pick one.
- **Any mention of price, ever, in a first cold email.** Not a figure, not a range, not
  "affordable". The offer is laid out later in the sequence once interest exists. A price
  in a stranger's first email is a number to decline before they have any reason to want
  the thing.
- Any sentence the reader could take as "you qualify" or "you could get this."
- Anything that reads as though it could have been sent to any __AUDIENCE__ in the country.\
"""


def writing_standard(audience: str = "organization", extra_avoid: str = "") -> str:
    """The house writing standard, with the audience noun substituted.

    ``audience`` is the singular noun for the reader's institution — "organization" for
    the nonprofit track, "school" for the schools track. ``extra_avoid`` is appended to
    the universal avoid-list as extra bullets, for things that are genuinely specific to
    one market (education jargon, for instance, only matters when writing to schools).
    Pass it pre-formatted as markdown bullets.
    """
    text = _STANDARD.replace(AUDIENCE_TOKEN, audience)
    if extra_avoid:
        text = f"{text}\n{extra_avoid.rstrip()}"
    return text
