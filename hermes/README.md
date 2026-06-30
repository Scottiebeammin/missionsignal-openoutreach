# Grounded Research Engine (Hermes → gated import)

How Anansi Atlas pulls **live, verified** funders/partners/government/resources/opportunities
from across the web — local & county government, regional & corporate funders, business
giving pages, and X/Twitter announcements — without hallucinations.

## The pipeline

```
Hermes (web research)  →  research JSON  →  import_hermes_research  →  grounding gate  →  Opportunity/Funder DB
   firecrawl + web                            (import_research_data)     reject fake/no-URL
   + x_search                                                            records, save the rest
```

Two complementary ingestion tracks feed the same database:

| Track | Source | Cost | Verification |
|---|---|---|---|
| **Federal grants** | `manage.py pull_grants_gov` → Grants.gov API | free | authoritative (auto `verified`) |
| **Everything else** | Hermes web research → gated import | Hermes/Nous subscription | grounding gate (`needs_review`) |

## Why Hermes

Hermes (`~/.hermes`) has live web tools — `web_tools.py` + firecrawl (search/extract),
`x_search_tool.py` (X/Twitter), and research skills. It can reach the sources a plain
LLM can't (local gov portals, corporate giving pages, live announcements), and it runs on
the existing Nous subscription — so research cost stays low. The runtime skill lives at
`~/.hermes/skills/anansi-atlas/SKILL.md`; the version-controlled copy is
`anansi-atlas-research-skill.md` in this folder (keep them in sync).

## The grounding gate (why nothing fake gets in)

`openoutreach/funding/grounding.py` is the single chokepoint. Every researched record must
carry a real `source_url`. Records with **no URL** or an **RFC-reserved placeholder domain**
(`.example.com` / `.test` / `.invalid` / `.localhost` — the exact signature of the 9
hallucinated Cleveland funders we found) are **rejected and never saved**. The import reports
`rejected: N` so dropped records are never silent.

`import_research_data` applies a fast, no-network reserved-domain check on every import.
`grounding.verify_source_url()` additionally does a live reachability check (used by the
source-agnostic `ingest_verified_opportunities` and the `audit_funder_links` command).

## Run it

```bash
# 1. Federal grants (free, authoritative) — for a project:
python manage.py pull_grants_gov --project-id <id>

# 2. Hermes research → JSON, then import (local or on Render for prod):
python manage.py import_hermes_research data/hermes_<org>_<date>.json --project-id <id> --dry-run  # validate
python manage.py import_hermes_research data/hermes_<org>_<date>.json --project-id <id>            # write

# 3. Audit existing funder links for hallucinations / dead URLs:
python manage.py audit_funder_links               # report
python manage.py audit_funder_links --archive-fake # deactivate fakes
```

## Deferred

**Twitter/X direct ingestion via the paid X API** — not worth it (~$100/mo for tiny limits,
anti-scraping ToS). Hermes's `x_search` already reads public X announcements as *leads*; the
skill instructs it to then cite the linked **official page** as the source URL, not the tweet.
