# Grant Builder — data model

Migration: `openoutreach/grants/migrations/0001_initial.py`. Purely additive — three new
tables, no change to any existing model or migration.

## GrantApplication

One grant-writing workspace = one (project, opportunity) pair.

| Field | Notes |
| --- | --- |
| `project` | FK `core.Project` — the ownership boundary; the organization is `project.organization` |
| `opportunity` | FK `funding.Opportunity` |
| `funding_signal` | optional FK `funding.FundingSignal`, `SET_NULL` — future-ready link to the discovery pipeline |
| `title`, `funder_name`, `deadline`, `requested_amount`, `source_url` | denormalized at creation so the draft still reads correctly if the inventory row is later re-scored, re-imported, or archived |
| `status` | Not Started / Drafting / Needs Information / Ready for Review / Final Review / Submitted / Awarded / Declined / Withdrawn |
| `created_by`, `created_at`, `updated_at` | |

Constraint: `UniqueConstraint(project, opportunity)` — "Start Grant Draft" is idempotent;
a second click continues the existing draft.

**`completion_percent` is a method, not a column.** It is derived from real section
status on every read: approved = 1.0, drafted = 0.5, needs-information = 0.25,
not-started = 0. Optional sections only count once started. A stored percentage could
drift out of step with the sections it claims to summarize; a derived one cannot.

## GrantApplicationSection

One answer.

| Field | Notes |
| --- | --- |
| `application` | FK, `CASCADE` |
| `section_key` | stable key from `services/template.py`; survives reordering and template swaps |
| `title`, `order`, `required` | copied from the spec at creation |
| `funder_question` | the funder's real wording when known, otherwise the template's |
| `guidance` | JSON list — what a strong response needs |
| **`draft_response`** | AI or in-progress text |
| **`approved_response`** | human-approved text |
| `word_limit`, `character_limit` | optional, per question |
| `status` | Not Started / Needs Information / Drafted / Approved |
| `source_fields` | JSON `[{"key", "label"}]` — the traceability record |
| `missing_information` | JSON list of human labels |
| `last_generated_at`, `approved_at`, `approved_by` | |

Constraint: `UniqueConstraint(application, section_key)`.

**Why two text columns.** Keeping the AI draft and the approved answer in separate
columns is the mechanism behind "AI never silently overwrites an approved answer".
Generation only ever writes `draft_response`; only `applications.approve_section` writes
`approved_response`, and no AI path calls it. `current_text` returns the approved text
when it exists, so the application always shows the human answer while an alternative
draft can sit beside it. Regeneration also leaves an approved section's *status* alone.

## GrantAnswerLibraryItem

An approved answer promoted to organization-level reusable knowledge.

| Field | Notes |
| --- | --- |
| `organization` | FK `core.Organization` — **organization-level**, so answers travel across projects and applications |
| `project` | optional FK, `SET_NULL` |
| `category` | 19 categories (Mission, Statement of Need, Organizational Capacity, …) |
| `title`, `answer` | |
| `approval_status` | Approved / Draft / Archived |
| `source_application`, `source_section` | `SET_NULL` — deleting an old application never destroys the organization's knowledge |
| `source_grant_title`, `source_fields`, `tags` | |
| `created_by`, `updated_by`, `created_at`, `updated_at` | |

Index: `(organization, category)` — the suggestion lookup on every section page.

## Why there is no `GrantApplicationSource` table

The brief allowed one. Source traceability is instead a JSON list on the section
(`source_fields`), which matches how this project already stores structured provenance:
`FundingSignal.score_breakdown`, `Funder.source_references`, `Opportunity.source_urls`,
`Lead.company_intel`. The data is always read with its section, never queried across
sections, and never joined. A join table would add a migration and a query for no
capability. If cross-application source analytics are ever needed, the JSON can be
promoted to a table without changing any caller — `context_builder` is the only producer.
