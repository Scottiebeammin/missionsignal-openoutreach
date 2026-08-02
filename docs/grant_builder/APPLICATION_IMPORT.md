# Grant Builder V1.1 — Real Application Import + Question Mapping

V1 answered *"help me write a grant."* V1.1 answers the harder question a real
client actually has: **"this funder asked me these eleven things — what do I do?"**

The organization pastes the real application. Atlas replies with four things:

| | |
|---|---|
| **What is this funder asking?** | The questions, verbatim, with their limits and requirements |
| **What does Atlas already know?** | Known by Atlas — facts read from real records |
| **What do I still need to provide?** | Needs Your Input — each gap with somewhere to fix it |
| **What should I emphasise?** | Suggested by Atlas — advice, never dressed up as fact |

## User flow

```
Grant draft → Import Application Questions
   → paste the application text  (+ optional title / funder / deadline / amount)
   → Analyze Application            ← parsing only; nothing is drafted here
   → Application Review             ← human corrects the parser, always
        edit wording · change section · fix limits · required/optional
        delete a bad question · add a missed one · reorder
   → Save Application Questions
        ↓
   Each question becomes a workspace section with the funder's exact wording
        ↓
   Known by Atlas / Needs Your Input / Suggested by Atlas
        ↓
   Ready to Draft  ─or─  More Information Needed
```

## Parser architecture

`services/application_parser.py` is **deterministic — regex and heuristics, no
LLM**. Three reasons, in order of importance:

1. **Fidelity.** A model that paraphrases a question has changed what the
   organization is answering. Every question is preserved byte-for-byte in
   `original_question`, which is written once and never rewritten.
2. **Testability.** "Maximum 500 words" must become `word_limit=500` *every*
   time. Each rule is pinned by a test.
3. **Availability.** Import works with no LLM key configured, like the rest of
   the non-drafting half of Grant Builder.

It detects section headings, question boundaries (numbered, lettered, `Q1.`,
`?`-terminated, and imperative prompts), per-question instructions, word limits,
character limits, page limits (recorded as a note — Atlas cannot count the
funder's pages), required/optional, attachments, and question type.

**It reports its own uncertainty.** `parse_confidence` is high/medium/low, with
`parse_notes` saying what it was unsure of, and any text it could not place is
surfaced on the review screen rather than dropped. Low confidence shows
*"Atlas may need help identifying these questions."* Nothing is ever saved
without a person passing through the review screen.

### Question types

`narrative`, `short_text`, `long_text`, `numeric`, `currency`, `date`, `yes_no`,
`multiple_choice`, `attachment`, `informational`, `unknown`.

Only `DRAFTABLE_TYPES` (narrative / long / short / unknown) are offered a draft —
Atlas does not write prose for a Yes/No box. `informational` and `attachment`
questions are excluded from completion entirely: a contact field is not an
answer someone writes.

## Data model

Extends `GrantApplicationSection` rather than creating a parallel model, so every
V1 capability (limits, approval protection, source traceability, Answer Library)
applies to imported questions unchanged.

| Field | Purpose |
|---|---|
| `original_question` | The funder's exact wording. Written once, never rewritten. |
| `funder_question` | The editable working copy. |
| `source_type` | `template` / `imported` / `manual` |
| `question_type` | See above |
| `section_group` | The funder's own heading |
| `instructions` | Per-question guidance printed on the form |
| `imported_order`, `imported_label` | Position and the funder's numbering |
| `import_batch` | FK to the paste it came from |
| `scoring_notes`, `page_limit_note`, `attachment_requirement` | Recorded, shown, not enforced |

Two new models:

- **`GrantApplicationImport`** — the paste itself, verbatim, plus confidence,
  notes, and application-level instructions. The source text survives so that if
  the parser got something wrong, the original is still there to re-read. Atlas
  never has only its own interpretation of what the funder asked.
- **`GrantAttachmentRequirement`** — the checklist. Reuses the Document Vault's
  own `DocumentType` vocabulary and links to a `DocumentVaultItem` where one
  exists, so the vault stays the single home for documents. V1.1 is
  checklist-only; no document storage was duplicated.

Migration: `grants/0002_grantapplicationsection_attachment_requirement_and_more.py`
(additive — new columns and two new tables).

## Knowledge mapping — the three-bucket trust model

`services/question_analysis.py`. The separation is enforced **by type**, not by
remembering to be careful in a template:

| Bucket | Type | Rule |
|---|---|---|
| Known by Atlas | `Fact` | Only from `context_builder` — real values from real records |
| Needs Your Input | `MissingFact` | An unmet requirement, with a hint and a portal destination |
| Suggested by Atlas | `Suggestion` | Advice. Asserts nothing. Has no `value` field at all. |

A `Suggestion` cannot be rendered as a fact card because it has no value to
render. That is deliberate: **a recommendation is not an organizational fact, and
a model inference is not an organizational fact.**

An imported question is free text, so it is matched against a **topic map** —
fourteen topics (mission, need, population, program, goals, implementation,
outcomes, capacity, partnerships, sustainability, budget, geography, equity,
history), each tying question wording to the facts that answer it and the
requirements it depends on. That keeps the mapping explainable: *this was treated
as a capacity question because it mentions staff and experience.*

## Generation gate

Atlas does not draft everything automatically. `can_generate_draft` plus a plain
`gate_reason`:

- **not a narrative type** → refused: *"fill it in directly rather than drafting prose"*
- **fewer than two supporting facts** → **More Information Needed** + *Add Information*
- **facts present, some gaps** → **Ready to Draft**, and the draft will carry
  visible `[Information needed: …]` placeholders
- **facts present, no gaps** → **Ready to Draft**

The gate is enforced in the view, not only in the UI: a POST to generate a
closed-gate question never reaches the LLM.

## Answer Library integration

Matched by topic → library category. Each match offers **Adapt for this
question** (copies into the *draft* column, never touching the saved item) or
**Replace draft**. Reuse is still refused on an already-approved section.

### Staleness — deliberately simple

Any number in a saved answer that does not appear anywhere in the current fact
corpus is surfaced:

> **Possible outdated information.** This answer states 275, which Atlas cannot
> match to your current organization data. Check it before reusing.

Plus an age note past twelve months. It does **not** try to understand what the
number means — a basic reliable check beats a clever unreliable one. Adding the
real figure to the Evidence Library resolves it permanently.

## Grant Coach for imported questions

Five dimensions, each a **label** (Strong / Moderate / Needs Attention /
Incomplete) with an explanation and one concrete improvement. No invented
percentages.

1. **Answered the Question** — does the response engage the terms the funder used?
2. **Evidence** — are factual claims supported by Atlas data?
3. **Specificity** — concrete detail, or filler?
4. **Funder Alignment** — does it connect to the opportunity's priorities?
5. **Readability** — sentence length, and limit compliance.

Overall = the weakest dimension. An answer is only as good as its worst part.

## Completeness

`answerable_sections()` switches the yardstick: once the real application is
imported, the funder's questions replace the 14-section template, so "7 of 10"
always means the funder's ten. Template rows are kept (an org may have drafted
against them first) but stop counting. The review adds a **Required Questions
Complete** metric, counts questions needing organization information, flags limit
violations, and lists unconfirmed attachments.

## Factual integrity — unchanged

Every V1 safeguard carries forward untouched. Importing a real application does
**not** weaken anti-fabrication:

- the closed fact set is still the only permitted source of substance
- `[Information needed: …]` is still the only way to handle a gap
- `unsupported_numbers()` still re-scans the written answer for untraceable figures
- `draft_response` and `approved_response` are still separate columns; generating
  never touches approved text or its status

## Limitations

- **Pasted text only.** No PDF, Word, or URL ingestion.
- **Page limits are recorded, not enforced** — Atlas counts words and characters.
- **Scoring criteria** are stored and displayed when explicitly stated, not inferred.
- **Topic matching is keyword-based.** An unusually-worded question may map to no
  topic; it still gets baseline facts and can be drafted, just with less targeting.
- **Staleness is numeric only.** A stale *claim* with no number will not be caught.
- **Attachments are a checklist.** No upload; linkage to the Document Vault only.

## Extension points left open

| Future | Where it plugs in |
|---|---|
| PDF / Word upload | `parse_application(text)` takes text — add an extractor in front of it |
| Application URL | Same seam, plus a fetcher |
| Funder-specific templates | `template.sections_for()`, already the V1 seam |
| Better parsing | An LLM pass could *propose* alongside the deterministic parse; the review screen is already the human gate |
| Document upload | `GrantAttachmentRequirement.linked_document` already points at the vault |
