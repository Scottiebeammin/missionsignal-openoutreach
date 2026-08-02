# Grant Builder — architecture

## Systems reused, not rebuilt

Grant Builder introduces one new Django app and no new subsystems. Everything it needs
already existed in Atlas:

| Need | Existing Atlas system used |
| --- | --- |
| Organization facts | `core.Organization` (mission, summary, focus areas, beneficiaries, geographies, capabilities, outcomes, partnerships, funding sources, budget range) |
| Program facts | `core.Project` (`programs`, `program_summaries`, `intake_notes`) |
| Opportunity + funder facts | `funding.Opportunity` (the project-scoped inventory row the portal already shows) |
| Discovery-pipeline link | `funding.FundingSignal` — optional FK, populated when a draft starts from a matched signal |
| Analyzer-derived criteria | `funding.FundingCriteria` (`program_areas`, `funding_use_categories`) |
| Hard evidence | `funding.EvidenceLibraryItem` — the only place a *number* (`metric_value`) can legitimately come from |
| Documents | `funding.DocumentVaultItem` (budget, board list, determination letter) |
| Readiness | `signals.readiness.build_organization_completeness` — the same score the Readiness dashboard shows |
| Permissions | `signals.views.client_project` — the single project-ownership gate every portal page uses |
| LLM | `core.llm.get_llm_model` + `run_agent_sync` (pydantic-ai, provider from `SiteConfig`) |
| Design system | `signals/templates/signals/_app_shell_{styles,sidebar,footer}.html` |

Nothing above was modified. The only changes to existing files are additive: an
`INSTALLED_APPS` entry, a URL include, a sidebar link, and the "Start Grant Draft"
action on the opportunity workspace.

## Layering

```
views.py                    thin — permissions, form handling, redirects
  └── services/             all logic; no LLM calls or ORM sprawl in views or templates
        context_builder     ← the ONLY module that reads Organization/Project/Evidence/Documents
        template            pure data: sections + information requirements
        applications        workspace lifecycle + grant readiness
        draft_generator     the ONLY module that talks to an LLM
        grant_coach         pure functions over (section, context) — no I/O
        completeness        pure functions over (application, context, sections)
        answer_library      organization-scoped reads/writes
```

`context_builder.build_grant_context(application)` is the single reuse boundary. Views,
the drafter, the coach, and the review all consume the same `GrantContext`. Adding a new
organization field to Grant Builder means adding one row to the fact table in that
module — no template or view changes.

## Permissions

Every view resolves the project through `client_project(request, pk)`, which filters on
`users=request.user` (staff may view-as-client). Objects are then fetched *through* that
project:

```python
application = get_object_or_404(GrantApplication, pk=application_id, project=project)
section     = get_object_or_404(GrantApplicationSection, application=application, section_key=key)
item        = get_object_or_404(GrantAnswerLibraryItem, pk=item_id, organization=project.organization)
```

There is no query in the app that can return another organization's data. `answer_library`
has no function that takes an organization-free queryset. Covered by four tests.

## Readiness integration

Grant Builder does not compute a second, unrelated readiness score.
`applications.build_grant_readiness` averages:

- the **organization** half — `build_organization_completeness(project).score`, unchanged
  from the Readiness dashboard, and
- the **application** half — the share of template sections whose information
  requirements are all satisfied.

That answers the question readiness could not answer before: *how ready are we to
actually complete this application?* The Missing Information tab is the actionable
version of the same data.

## Template flexibility

`services/template.py` holds the standard 14-section template as a tuple of frozen
`SectionSpec`s, resolved through `sections_for(opportunity)`. Sections are persisted per
application with a stable `section_key`, and `sync_sections` only ever *adds* rows — it
never rewrites an existing question, limit, or answer.

That is the seam for funder-specific templates: return a different section list from
`sections_for()` and everything downstream (drafting, coach, review, library categories)
follows, with no schema change and no data loss on existing drafts.

## LLM provider independence

Grant Builder never talks to a model vendor. It calls `core.llm.get_llm_model()` and
`run_agent_sync()`, and that is the whole of its knowledge about inference. The provider
is chosen in `SiteConfig` (Django Admin), so switching vendors is configuration, not code:

```
Grant Builder → core.llm → provider builder → Anthropic | OpenAI | any OpenAI-compatible server
```

`core.llm` ships seven builders (`openai`, `anthropic`, `google`, `groq`, `mistral`,
`cohere`, `openai_compatible`). The `openai_compatible` builder takes `llm_api_base` and
therefore already reaches **any OpenAI-compatible inference server** — a self-hosted
open-weight model behind vLLM, TGI, or Ollama included. This was verified end to end
against a local Ollama server: Atlas built a working model client with **zero code
changes**, purely from `SiteConfig`.

Two rules keep this true, both enforced by tests in
`tests/missionsignal/test_grant_llm_provider.py`:

- **No provider SDK may be imported inside `openoutreach/grants/`.** The Anthropic and
  OpenAI SDKs are imported only in `core/llm.py`.
- **No provider or model name may appear in Grant Builder source.** Model IDs are
  free-text `SiteConfig` values, so adopting a new model needs no release.

### Structured output is the binding requirement

Drafting uses pydantic-ai's `output_type=SectionDraft`, which is implemented with
**tool/function calling**. Any candidate model must call tools reliably — prose-only JSON
is not sufficient. A model that cannot do this fails with
`UnexpectedModelBehavior: Exceeded maximum output retries`, regardless of how good its
writing is. This is the first thing to test when evaluating a new provider or model, and
small models (≈3B) commonly advertise tool support without delivering it.

### No production dependency on developer hardware

Local inference is a **development and evaluation** convenience only. Production Atlas
must never point at a developer's machine: `llm_api_base` in a deployed environment
resolves to a hosted endpoint (a vendor API, or a dedicated inference server), never to
`localhost`. Moving from a laptop to a dedicated GPU server changes three `SiteConfig`
fields and nothing else in this codebase.

## Extension points already in place

| Future capability | What already supports it |
| --- | --- |
| Grant application import (paste a URL / PDF / questions) | `sections_for()` seam; `funder_question`, `word_limit`, `character_limit` are per-section columns a parser can fill |
| Funder-specific templates | same seam; `section_key` is stable across templates |
| Document library reuse | `DocumentVaultItem` already feeds the context and the requirements |
| External evidence research | `Fact` carries a source label; a researched fact would enter the same registry with its citation as the label |
| Collaborative writing | `approved_by` / `approved_at` per section, `created_by` per application |
| Submission tracking | `GrantApplication.Status` already runs to Submitted / Awarded / Declined / Withdrawn |
| Word/PDF export | `grant_export` renders the whole application in one document; print-to-PDF works today, a generator would render the same context |
| Self-hosted open-weight model | `openai_compatible` provider + `llm_api_base`; point it at a vLLM/TGI/Ollama server. No Grant Builder change |
