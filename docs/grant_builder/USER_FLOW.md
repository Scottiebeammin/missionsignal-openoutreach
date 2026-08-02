# Grant Builder — user flow

## 1. Start from an opportunity

On any opportunity workspace (`/projects/<pk>/opportunities/<id>/`) the Recommended Next
Step panel now carries **Start Grant Draft**. If a draft already exists it reads
**Continue Grant Draft** with the current completion percentage.

Grant Builder is also reachable directly from the sidebar (Act → Grant Builder), which
lists every draft on the project and shows an empty state pointing at Browse
Opportunities when there are none.

## 2. The workspace is created

`start_grant_application` captures the opportunity's facts (name, funder, deadline,
funding amount, source URL) and creates one section per template entry — 14 sections, 13
required, all Not Started. Starting twice never duplicates.

## 3. Overview — what Atlas knows and what it doesn't

- **Grant Preparation Readiness** — e.g. *54% · Developing*
- **Sections Atlas can draft now** — e.g. *8 of 14*
- **Organization Completeness** — carried straight from the Readiness dashboard
- **Issues before submission**
- **Still needed** — the top gaps, each with a hint
- **What Atlas already knows about you** — the complete fact set, with human-readable
  source labels, that any generated answer may draw on

## 4. Write a section

Each section page shows, in order:

1. **Funder question** — editable, so a real application's wording can replace the
   template's
2. **Atlas guidance** — what a strong response usually needs
3. **Information needed** — the gaps, each with an **Add Information** / **Add
   Evidence** / **Add to Document Vault** button pointing at the right portal page
4. **Draft / approved response** — labeled *AI draft — not approved* or *Approved*, with
   a live word/character counter that turns red past the limit
5. **Atlas actions** — Generate/Regenerate, Improve, Shorten, Expand, Make More Specific,
   Improve Clarity, Align to Funder
6. **Grant Coach** — Strong / Needs Work / Missing Evidence / Possible Mismatch /
   Unsupported Claim findings, most serious first
7. **Save to Answer Library** — appears once the answer is approved

The sidebar of the page carries **Sources used**, **What Atlas knows for this section**,
and **From your Answer Library** (approved answers worth adapting, with Reuse / Replace).

## 5. Missing Information

One table of every gap: what it is, why it matters, which sections it blocks, and the
button that goes to the page where it can be supplied. This is the screen that turns
"our draft is weak" into a to-do list.

## 6. Answer Library

The organization's approved answers, filterable by category, each showing its source
grant and the Atlas fields it was built from. Any item can be reused into any section of
the current application — appended to the draft or replacing it. The original is never
changed, and reuse is refused on an already-approved section.

## 7. Review

Five metrics, each with the basis it was computed from, and the full issue list:

```
4 issues before submission
  Goals and Objectives   2 placeholders still need filling: measurable target; baseline
  Sustainability         No response drafted yet.
  Budget Narrative       Contains figures Atlas cannot trace to your organization data (48000).
  Statement of Need      Response exceeds the funder's 2,000-character limit.
```

Each issue links straight to the section that owns it.

## 8. Export / handoff

The full draft view renders every answer in one document with:

- **Copy Full Draft** (all answers, headed by section)
- **Copy this answer** per section
- **Print / Save as PDF** (print stylesheet hides the shell and page-breaks cleanly)
- a list of sections not yet drafted

## 9. Status

Not Started → Drafting → Needs Information → Ready for Review → Final Review → Submitted
→ Awarded / Declined / Withdrawn. Set from the Overview or the Review screen. V1 tracks
status only — it is not a post-award grant management system.
