# Grant Builder — AI rules and the factual-integrity guarantee

## The rule

**Atlas never invents organizational facts.**

Specifically, the drafter may never produce a statistic, outcome, budget, dollar amount,
staff number, population served, year, date, funder relationship, partnership, government
relationship, prior grant award, program performance figure, or geographic claim that the
organization did not supply.

Facts may come only from:

1. information the organization entered into Atlas (`Organization`, `Project`,
   `EvidenceLibraryItem`, `DocumentVaultItem`),
2. approved Atlas records (the Answer Library), and
3. verified opportunity / funder data (`Opportunity`).

The AI may improve wording, structure, order, emphasis, and clarity. It may not add
substance.

## How it is enforced — three layers

A prompt alone is a wish. Grant Builder enforces the rule three times.

### 1. A closed fact set (`context_builder.py` → `draft_generator.py`)

The prompt does not describe the organization in prose. It carries a labeled block built
from real database rows — and only the facts the section's spec declares:

```
ORGANIZATION FACTS (the only permitted source of substance):

Organization Mission:
Close the opportunity gap by preparing young people…

Service Area:
Orlando, Orange, Florida…
```

Absent fields are simply not in the block, so there is nothing to paraphrase from.

### 2. The placeholder contract (`draft_generator.py`)

When a strong answer needs something that was not supplied, the drafter must write the
literal marker

```
[Information needed: <short description>]
```

in the sentence where the fact belongs, rather than estimating. The marker is
load-bearing, not cosmetic:

- the section workspace renders it inline,
- the section's status becomes **Needs Information**,
- the Review screen counts every unfilled placeholder as an open issue, and
- the Grant Coach reports it.

An un-filled placeholder therefore cannot quietly reach a funder.

### 3. Verification after the fact (`grant_coach.unsupported_numbers`)

The drafting prompt *asks* the model not to invent figures. This check *verifies* it
didn't — and catches figures a person typed in by hand too.

`context_builder` collects every numeric token appearing anywhere in the fact corpus into
`GrantContext.supported_numbers`. After generation (and on every view of a section), the
coach extracts the numeric tokens from the response, ignores anything inside an
`[Information needed: …]` marker, and reports any remainder:

> **Unsupported Claim** — This response contains figures Atlas cannot trace to your
> organization data (4318, 2500000). Confirm the number and add it to your profile or
> Evidence Library, or remove it.

The check is deliberately strict: a false positive costs one confirmation, a false
negative costs a funder's trust. Adding the real figure to the Evidence Library resolves
it permanently, because that figure then enters `supported_numbers`.

## Approval is a human act

- Generation writes **only** `draft_response`.
- `approved_response` is written **only** by `applications.approve_section`, which is
  called only from the human-driven save view. No AI code path reaches it.
- Regenerating an approved section produces an alternative draft *beside* the approved
  answer, and leaves the approved text, `approved_by`, `approved_at`, and the
  **Approved** status untouched.
- Only an **approved** answer can be saved to the Answer Library
  (`save_section_to_library` raises `ValueError` otherwise) — an unreviewed AI draft can
  never become the organization's reusable description of itself.
- Reusing a library answer copies it into the **draft** column and never modifies the
  library item; reuse is refused outright on an already-approved section.

Every generated response is visibly marked **AI draft — not approved** until a person
approves it.

## Refinement actions

Improve, Shorten, Expand, Make More Specific, Improve Clarity, and Align to Funder are
writing instructions layered on the same closed fact set and the same system rules. None
may introduce a new claim. Shorten is told to stay within the configured word/character
limit *without dropping any supplied fact*. Expand is told to say so rather than pad when
the facts are exhausted.

## Scores are counted, not guessed

The Review screen reports a number only where one can be counted (approved sections,
satisfied information requirements). Where a real score is not derivable — funder
alignment, evidence strength, budget alignment — it reports a label (Strong / Moderate /
Needs Attention / Incomplete) together with the basis it was derived from
("3 of 3 comparable dimensions overlap (focus area, population, geography)"). A fabricated
89% would be exactly the kind of unearned confidence this feature exists to remove.

## When no LLM is configured

`draft_generator` raises `DraftGenerationUnavailable` (a `GrantBuilderError`) when
`SiteConfig` has no usable LLM. The view surfaces it as a message. Every non-AI part of
Grant Builder — prefill, missing-information detection, the coach, limits, the Answer
Library, the review, and export — works with no LLM configured at all.
