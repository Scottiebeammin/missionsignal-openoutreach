# Architecture

Detailed module documentation for OpenOutreach. See `CLAUDE.md` for rules and quick reference.

## Project Layout

All source lives in the single `openoutreach/` package; Django apps are nested inside it
(dotted `AppConfig.name`, short labels). One engine, N outreach channels:

```
manage.py
tests/
openoutreach/
  settings.py        # Django settings (was linkedin/django_settings.py)
  urls.py
  core/              # engine app (label: core) — daemon, task queue + scheduler,
                     #   Campaign/SiteConfig/Task models, llm.py, conf.py, onboarding,
                     #   follow-up agent, db/ helpers, management commands, vendored mem0
  linkedin/          # channel app (label: linkedin) — browser/, pipeline/, ml/,
                     #   LinkedInProfile/SearchKeyword/ActionLog models, task handlers, setup/
  emails/            # channel app (label: emails) — email outreach (finder, Mailbox, icemail import, smtp auth, nudge; sender Layer 1 WIP)
  crm/               # app (label: crm) — Lead, Deal
  chat/              # app (label: chat) — ChatMessage
  signals/           # Anansi Atlas app (label: signals) — intake, deterministic analysis, Mission Brief, relationship tracking, and Signal dashboards
  sources/           # Anansi Atlas app (label: sources) — source/query/record tracking for discovery inputs
  funding/           # Anansi Atlas app (label: funding) — FundingSignal criteria, opportunity database records, opportunities, matches, feedback
```

Layering: `core` owns orchestration and channel-agnostic models; channel apps own their
platform mechanics, channel-bound models, and task handlers. `core` imports channel code
only at wiring points (the daemon's handler map, onboarding's profile setup).

## Entry Flow

`manage.py` — stock Django management entrypoint. Bare `python manage.py` (no args) defaults to `rundaemon`.

### `rundaemon` management command (`management/commands/rundaemon.py`)

Startup sequence:
1. **Configure logging** — DEBUG level, suppresses noisy third-party loggers (urllib3, httpx, pydantic_ai, openai, playwright, etc.).
2. **Ensure DB** — `migrate --no-input` + `setup_crm` (idempotent).
3. **Onboard** — checks `missing_keys()`; if incomplete: uses `--onboard <config.json>` (non-interactive), falls back to interactive wizard (TTY), or exits with clear error (no TTY).
4. **Validate** — `LLM_API_KEY`, active `LinkedInProfile`, at least one campaign.
5. **Session** — `get_or_create_session(profile)`, sets default campaign (first non-freemium).
6. **Newsletter** — GDPR override + `ensure_newsletter_subscription()` (marker-guarded, runs once).
7. **Run** — `run_daemon(session)`.

Docker `start` script handles only Xvfb/VNC setup, then `exec python manage.py rundaemon "$@"`.

### Other management commands

- `onboard` — standalone onboarding (interactive or `--non-interactive` with `--config-file` / individual flags).
- `setup_crm` — idempotent CRM bootstrap (default Site).
- `add_seeds` — add seed LinkedIn profile URLs to a campaign.

## Onboarding (`onboarding.py`)

`OnboardConfig` — pure dataclass with all onboarding fields. Two constructors:
- `OnboardConfig.from_json(path)` — from JSON file (cloud / non-interactive).
- `collect_from_wizard()` — interactive questionary wizard (needs TTY), only asks for `missing_keys()`. Backed by the vendored `onboarding_wizard.py` (step engine) + `onboarding_prompts.py` (`SELF_HOSTED_QUESTIONS`) — no external `openoutreach` dependency.

Single write path: `apply(config)` — idempotent, creates missing Campaign, LinkedInProfile, env vars, and legal acceptance. Four components:

1. **Campaign** — name, product docs, objective, booking link, seed URLs. Creates `Campaign` with M2M user membership.
2. **LinkedInProfile** — email, password, newsletter, rate limits. Django username from email slug.
3. **LLM config** — `LLM_PROVIDER`, `LLM_API_KEY`, `AI_MODEL`, `LLM_API_BASE` → writes to `SiteConfig` singleton in DB.
4. **Legal notice** — per-account acceptance stored as `LinkedInProfile.legal_accepted`.

## Profile State Machine

`crm/models/deal.py:DealState` (OpenOutreach-owned `TextChoices`) holds the CRM funnel: QUALIFIED, READY_TO_CONNECT, PENDING, CONNECTED, COMPLETED, FAILED, plus the **email fork** READY_TO_EMAIL → EMAILED. Enrichment at QUALIFIED *routes* (it doesn't gate) and the route is the fork — the state *is* the routing: a finder **hit** → QUALIFIED → READY_TO_EMAIL (ungated FIFO send-queue) → EMAILED on the single Layer-1 send (quasi-terminal, rests until a human sets an Outcome); a **miss / finder-off / couldn't-run** → stays QUALIFIED for the GP gate to promote to READY_TO_CONNECT (its only door; the connection harvests contact info on acceptance). The two fork states encode the one-shot guarantee in the state column (the email pool reads only READY_TO_EMAIL). **Enrichment is a one-shot, merged into qualify (not a standalone router):** the finder runs inline and synchronously in `_save_qualification_result` *at Deal creation*, before the deal is ever visible to the GP gate — that ordering is deliberate and makes the fork race-free (email wins by construction; the GP gate only ever sees finder-declined deals, so the two routings never compete for the same QUALIFIED rows). The flip side is that the finder runs **exactly once per lead, ever**: once a Deal exists the lead is excluded from qualification (`get_leads_for_qualification` does `.exclude(deal__campaign=...)`) and no other path calls the finder (the GP-gate promotion has no finder hook). So a lookup that never conclusively ran — no key yet, service unreachable, *or the process was interrupted mid-poll* — is **never retried**; the deal simply falls through to the connect leg. There is no enrichment-retry pool by design (one would race the GP gate). To force re-enrichment, **delete the Deal** so the lead re-qualifies from scratch. The funnel lives here, **not** in `linkedin_cli`: the library's connect/status verbs only *observe* QUALIFIED/PENDING/CONNECTED off the LinkedIn UI and return them as plain strings, which the task handlers lift via `DealState(value)` at the boundary. Pre-Deal states: url_only (Lead row exists but `embedding` is null), enriched (has `embedding`). `Lead.disqualified=True` = permanent account-level exclusion. LLM rejections = FAILED Deals with wrong_fit outcome (campaign-scoped).

`crm/models/deal.py:Outcome` (TextChoices): converted, not_interested, wrong_fit, no_budget, has_solution, bad_timing, unresponsive, unknown. Used by `Deal.outcome`.

## Task Queue

Persistent queue backed by `Task` model. Worker loop in `daemon.py`: `seconds_until_active()` guard pauses outside the daily active-hours window (single contiguous window, no weekend skip) → pop oldest due task → set campaign on session → RUNNING → dispatch via `_HANDLERS` dict → COMPLETED/FAILED. Failures captured by `failure_diagnostics()` context manager.

Task rows are **lazy**: `payload = {"campaign_id": <id>}` only — no `public_id`, no deal reference. The handler resolves a concrete target at execution time via a single eligibility query. Slot creation is centralized in `openoutreach/core/scheduler.py`; no other module inserts Task rows. The module is organized in three layers:

1. **Per-type slot creation** — two flavours. **Window planners** for the rate-limited LinkedIn channels (`plan_connect_window`, `plan_follow_up_window`, `plan_check_pending_window`): when no PENDING task of the type exists for a campaign, compute slot count `n` for the next 24h and insert `1 immediate + (n-1) Poisson-spaced` lazy rows (the leading immediate slot kills the cold-start ramp — without it the first action would sit `T/n` away on average, ~72 min for a 20/day campaign). **Eager drain** for email (`flush_email_queue`): email has no anti-bot rhythm to fake, so every READY_TO_EMAIL deal gets an *immediate* slot (no spacing, no ranking), capped by the pool-wide per-box daily headroom (`Mailbox.objects.remaining_today()`); also a no-op while a PENDING email task exists.
2. **State-transition hook** — `on_deal_state_entered(deal)`. For PENDING transitions, stamps `deal.next_check_pending_at = now + backoff_hours`. All other transitions are no-ops. Separately, `set_profile_state` itself fires a best-effort `Lead.capture_contact_info(session)` on the first CONNECTED transition (contact-info overlay scrape — the hook can't, it has no `session`); errors are logged and never fail the transition, `AuthenticationError` propagates.
3. **`reconcile(session)`** — Recovers stale RUNNING tasks, then per campaign runs the window planners and the email flush. Daemon calls it on startup and whenever the queue has no ready task.

Per-type recompute trigger: when a type's PENDING queue is empty for a campaign, the next idle reconcile re-plans only that type (the LinkedIn types re-plan a 24h window; email re-drains the READY_TO_EMAIL pool up to the remaining per-box cap). No global rollover, no leftover-slot reconciliation. `AuthenticationError` (401) triggers `session.reauthenticate()` then marks the task FAILED; the planner picks the type back up on the next idle cycle.

Three task types (handlers in `openoutreach/linkedin/tasks/`, signature: `handle_*(task, session, qualifiers)`):

1. **`handle_connect`** — Unified via `ConnectStrategy` dataclass. Regular: `find_candidate()` from `pools.py`; freemium: `find_freemium_candidate()`. Unreachable detection after `MAX_CONNECT_ATTEMPTS` (3). No self-rescheduling — the planner owns timing.
2. **`handle_check_pending`** — Eligibility query: oldest PENDING deal in the campaign with `next_check_pending_at <= now`. If none, mark task DONE. On still-PENDING outcome, double `backoff_hours` and re-stamp `next_check_pending_at`.
3. **`handle_follow_up`** — Eligibility query: oldest CONNECTED deal in the campaign with no recent outgoing message. If none, mark task DONE. Otherwise call `run_follow_up_agent()` (returns `FollowUpDecision`: `send_message`/`mark_completed`/`wait`) and execute deterministically.

## Qualification ML Pipeline

GPR (sklearn, ConstantKernel * RBF) inside Pipeline(StandardScaler, GPR) with BALD active learning:

1. **Balance-driven selection** — n_negatives > n_positives → exploit (highest P); otherwise → explore (highest BALD).
2. **LLM decision** — All decisions via LLM (`qualify_lead.j2`). GP only for candidate selection and confidence gate.
3. **READY_TO_CONNECT gate** — P(f > 0.5) above `min_ready_to_connect_prob` (0.9) promotes QUALIFIED → READY_TO_CONNECT.

384-dim FastEmbed embeddings stored directly on Lead model, per-campaign GP models at ``Campaign.model_blob` (BinaryField, joblib-dumped with `compress=3`)`. Cold start returns None until >=2 labels of both classes.

## Django Apps

Eight project apps in `INSTALLED_APPS`, all nested under the `openoutreach/` package (see Project Layout):

- **`core`** — Engine: SiteConfig, Campaign (with users M2M), Task models; daemon, scheduler, LLM factory, onboarding, follow-up agent.
- **`linkedin`** — LinkedIn channel: LinkedInProfile, SearchKeyword, ActionLog models; browser, discovery pipeline, ML qualification, task handlers.
- **`emails`** — Email channel (Layer 1 of the email-first pivot). `finder.py` resolves a work email for a qualified lead on demand (`resolve_email`); `bettercontact.py` is the one provider (submit→poll over the BetterContact API). **`Mailbox`** model (one SMTP inbox; host/port default to IceMail's Google boxes `smtp.gmail.com:587`); **`icemail.py`** `parse_mailboxes()` reads the `Email`/`Password` columns from a pasted *Export Mailboxes* block; **`smtp.py`** `verify_auth()` is the auth-only login check (no test send during warmup); **`nudge.py`** is the per-launch setup prompt (`email_state()` machine + GLF copy + `import_mailboxes()` = parse→store→auth-check). **`sender.py`** `send_email(mailbox, to, subject, body)` sends one message over the box's SMTP+STARTTLS creds and returns the Message-ID (no error handling by design — a failed send fails its task and is retried). **`tasks/send.py`** `handle_email` is the single-shot EMAIL task: pick the least-loaded under-cap `Mailbox` + the oldest READY_TO_EMAIL deal (`core.db.deals.get_emailable_deals`), compose via `core/agents/email_opener.py`, send, then `_record_sent_email` writes the email fields **and** `state=EMAILED` in one `deal.save()` (send record + state on the same row → no double-send window). Per-box daily-cap pacing lives on the `Mailbox` manager (`least_loaded_under_cap()`, `remaining_today()`, instance `sent_today()`/`headroom_today()`, keyed on `Deal.email_sent_at`). Layer 1 is outbound-only and never re-emails — follow-ups/replies are the hosted Layer-2 backend's job, reconstructed from the mailbox.
- **`crm`** — Lead (with embedding) and Deal models (in `crm/models/lead.py` and `crm/models/deal.py`). Also defines `Outcome` enum.
- **`chat`** — `ChatMessage` model (FK to the owning Deal, content, owner, answer_to threading, topic).
- **`signals`** — Anansi Atlas V1: public Anansi Atlas landing page, local interest capture, pilot onboarding entry, organization/project intake, deterministic analyzer orchestration, analysis review, Executive Dashboard route, Readiness Dashboard route, Relationship Intelligence route, Opportunity Web route, Opportunity Web Snapshot route, Celebrations route, Mission Brief, FundingSignal dashboard route, GovernmentSignal dashboard route, ResourceSignal dashboard route, PartnershipSignal dashboard route, Opportunity Matching dashboard route, Discovery Engine inventory route, EcosystemSignal overview route, module placeholder routes, score transparency helpers, project-scoped `OrganizationContact` and relationship `PartnerOrganization` records, `InterestSignup` records, and the `seed_missionsignal_demo` command.
- **`sources`** — Anansi Atlas source bookkeeping: `Source`, `SearchQuery`, and `SourceRecord` normalize discovery inputs and record identity so future ingestion can deduplicate opportunities by source and URL/external ID.
- **`funding`** — FundingSignal V2 data model, deterministic readiness layer, Opportunity Database Layer V1 foundation, Discovery Engine V2 inventory models, Opportunity Lifecycle V1 fields, Opportunity Work V1 task/deadline models, Pipeline Forecasting V1 value fields on `Opportunity`, and Document/Evidence V1 models: `FundingCriteria`, `Funder`, `GovernmentEntity`, `ResourceProvider`, `PartnerOrganization`, `SourceOrganization`, `Opportunity`, `OpportunityTask`, `OpportunityDeadline`, `DocumentVaultItem`, `EvidenceLibraryItem`, `OpportunityDocumentRequirement`, `FundingOpportunity`, `FundingOpportunitySource`, `FundingSignal`, and `FundingSignalFeedback`, plus identity helpers, opportunity resolution services, CSV opportunity import, readiness dashboard helpers, and deterministic forecast helpers in `signals.forecasting`. Executive UX Consolidation keeps these capabilities intact while shifting templates toward summary-first dashboards, compact operating boards, and collapsed secondary details.

History note: core's models lived in the linkedin app until mid-2026; the move was state-only
plus table renames (`linkedin_campaign` → `core_campaign` etc., `core.0002_rename_engine_tables`).

## CRM Data Model

- **SiteConfig** (`core/models.py`) — Singleton (pk=1). `llm_provider` (TextChoices: openai/anthropic/google/groq/mistral/cohere/openai_compatible), `llm_api_key`, `ai_model`, `llm_api_base`, `finder_api_key` (BetterContact email-finder key; blank disables enrichment — see `emails/finder.py`). Accessed via `SiteConfig.load()`; `core/llm.py:get_llm_model()` is the single factory that turns it into a `pydantic_ai.models.Model`.
- **Campaign** (`core/models.py`) — `name` (unique), `users` (M2M to User), `product_docs`, `campaign_objective`, `booking_link`, `is_freemium`, `action_fraction`, `seed_public_ids` (JSONField).
- **Organization** (`core/models.py`) — Anansi Atlas-owned nonprofit/mission identity and analyzer profile. Stores required intake (`name`, `website`, `mission`), optional geography/funding/partnership context, analyzer outputs (`organization_summary`, `focus_areas`, `beneficiaries`, `capabilities`, `search_keywords`), status/confidence/warnings, and user access via `missionsignal_organizations`.
- **Project** (`core/models.py`) — An organization initiative used to scope FundingSignal work. Stores project/program narrative, analyzer-produced `program_summaries`, active flag, and user access via `missionsignal_projects`.
- **LinkedInProfile** (`linkedin/models.py`) — 1:1 with User. `self_lead` FK to Lead (nullable, set on first self-profile discovery). Credentials, rate limits (`connect_daily_limit`, `follow_up_daily_limit` — daily-only; LinkedIn's own weekly ceiling surfaces at the handler boundary via `ReachedConnectionLimit`). Methods: `can_execute`/`record_action`/`mark_exhausted`. In-memory `_exhausted` dict for daily rate limit caching.
- **SearchKeyword** (`linkedin/models.py`) — FK to Campaign. `keyword`, `used`, `used_at`. Unique on `(campaign, keyword)`.
- **ActionLog** (`linkedin/models.py`) — FK to LinkedInProfile + Campaign. `action_type` (connect/follow_up), `created_at`. Composite index on `(linkedin_profile, action_type, created_at)`.
- **Lead** (`crm/models/lead.py`) — Per LinkedIn URL (`linkedin_url` = unique). `public_identifier` (derived from URL, unique). `urn` = unique CharField (LinkedIn entity URN, cached on first scrape). `embedding` = 384-dim float32 BinaryField (nullable). `disqualified` = permanent exclusion. **Email storage = one field per source:** `contact_info` (nullable JSON — raw LinkedIn contact-info overlay `{email, emails, phone_numbers}`, captured once at CONNECTED; null = never scraped, the idempotency flag) and `api_email` (nullable EmailField — enrichment-API result; null = not found). `resolve_api_email()` populates it via the finder at qualification (tri-state: True hit / False genuine-miss / None finder-unavailable; cached on a hit). **The finder is called exactly once per lead — inline at Deal creation — and never retried** (the lead is excluded from qualification once a Deal exists, and no other path calls it); the tri-state's "free to retry on a miss/unavailable" only holds within that single inline call, *not* across daemon cycles. Re-enrichment requires deleting the Deal. See the email-fork note under `DealState` above. On a **hit** the qualify router routes the Deal QUALIFIED → `DealState.READY_TO_EMAIL` (onto the email channel, out of the connect pool); a miss / finder-unavailable leaves it QUALIFIED for the connect leg. The parsed profile dict, person name, and company name are **not stored** — they live only in memory for the lifetime of a scrape dict. Callers that need them re-scrape via `lead.get_profile(session)`. `embedding_array` property for numpy access. `embed_from_profile(profile)` computes + persists the embedding from an in-hand dict (skips the scrape). `get_labeled_arrays(campaign)` classmethod returns (X, y) for GP warm start. Labels: non-FAILED state → 1, FAILED+wrong_fit → 0, other FAILED → skipped.
- **Deal** (`crm/models/deal.py`) — Per campaign (campaign-scoped via FK). `state` = CharField (`DealState` choices — the OpenOutreach-owned funnel, incl. the READY_TO_EMAIL/EMAILED fork). `outcome` = CharField (Outcome choices: converted/not_interested/wrong_fit/no_budget/has_solution/bad_timing/unresponsive/unknown). `reason` = qualification reason (free text). `connect_attempts` = retry count. `backoff_hours` = check_pending backoff. `next_check_pending_at` = DateTimeField (indexed) stamped by `on_deal_state_entered(PENDING)`; the `check_pending` eligibility query and `plan_check_pending_window` both read it. **Email send record (Layer 1):** `mailbox` = FK to the sending `Mailbox` (cap/audit), `email_subject`, `email_message_id` (Layer-2 campaign-correlation key), `email_sent_at` (the per-box cap ledger) — all written atomically with `state=EMAILED` on the single send; the body is not stored (Layer 2 reconstructs the thread from the mailbox). `profile_summary` / `chat_summary` = JSONField fact lists (lazy, mem0-style, campaign-scoped). `creation_date`, `update_date`.
- **Task** (`core/models.py`) — `task_type` (connect/check_pending/follow_up/email), `status` (pending/running/completed/failed), `scheduled_at`, `payload` (JSONField), `started_at`, `completed_at`. Composite index on `(status, scheduled_at)`.
- **ChatMessage** (`chat/models.py`) — FK to the owning **Deal** (the per-(lead, campaign) conversation; `related_name="messages"`). `content`, `is_outgoing`, `owner`, `linkedin_urn` (Voyager entityUrn, used for dedup), `answer_to` (self FK), `topic` (self FK), `recipients`, `to` (M2M to User). Dedup is per-deal: `unique(deal, linkedin_urn)` — a shared LinkedIn DM thread is materialized once per live deal. (Replaced the original GenericForeignKey-to-Lead in `chat/0003`.)
- **OrganizationAnalysisRun** (`signals/models.py`) — Analyzer run ledger for Anansi Atlas. Captures input/output snapshots, status, errors, analyzer version, and timing for deterministic V1 analysis and later analyzer backends.
- **OrganizationSourcePage** (`signals/models.py`) — Source URL metadata tied to an Organization, unique per `(organization, url)`, used to preserve the evidence set behind an analysis.
- **FundingCriteria** (`funding/models.py`) — One row per Project. Stores inferred applicant types, funder/opportunity types, focus areas, beneficiaries, geographies, program areas, funding uses, amount range, deadline horizon, scoring weights, analyzer confidence, and the source analysis run.
- **Opportunity Database Layer V1 / Discovery Engine V2 / Opportunity Lifecycle V1 inventory** (`funding/models.py`) — Foundation records for deterministic matching and future discovery: `Funder`, `GovernmentEntity`, `ResourceProvider`, and `PartnerOrganization`. Discovery Engine V2 adds `SourceOrganization` and enriches `Opportunity` as a manually managed inventory record with type, source owner, source name/type, geography, focus areas, beneficiaries, eligibility notes, expanded status, posted/deadline dates, priority, and notes. Opportunity Lifecycle V1 adds lifecycle status (`Discovered`, `Reviewing`, `Qualified`, `Pursuing`, `Application Drafting`, `Submitted`, `Awarded`, `Declined`, `Closed`) plus assigned-owner, lifecycle-notes, and status-history placeholders for future collaboration. These records are admin-manageable and seeded with varied BridgeForward-style demo examples, but they do not perform search, scraping, API calls, agents, AI discovery, embeddings, vector search, or matching automation.
- **FundingOpportunity** (`funding/models.py`) — Normalized opportunity identity and details. Identity is derived from canonical URL when present, otherwise funder/title/deadline/type, allowing source records to converge on one opportunity.
- **FundingSignal** (`funding/models.py`) — Project-to-opportunity match with lifecycle state, score/confidence, eligibility status, score breakdown, explanation, owner, priority, and feedback.
- **FundingReadiness** (`funding/readiness.py`) — Deterministic V2 dashboard output. Produces readiness score/level, strengths, gaps, inferred funding themes, scored recommended funder types, a Local Government Opportunity Snapshot, complete/missing grant readiness checklist rows, and gap-specific recommended funding actions. Local Government is a first-class recommendation and covers city grants, county grants, youth services funding, workforce programs, economic development programs, digital equity initiatives, community development programs, public-sector service contracts, and RFPs.
- **Source/SearchQuery/SourceRecord** (`sources/models.py`) — Discovery-source registry, per-project query tracking, and raw result records. `SourceRecord` supports source-local external ID and canonical URL deduplication and can link back to the search queries that found it.

## Key Modules

Paths below are relative to `openoutreach/`.

- **`core/daemon.py`** — Worker loop with active-hours guard (`ENABLE_ACTIVE_HOURS` flag, `seconds_until_active()`), `_build_qualifiers()`, freemium import, `_CloudPromoRotator`. Calls `scheduler.reconcile()` when the queue has no ready task.
- **`linkedin/diagnostics.py`** — `failure_diagnostics()` context manager, `capture_failure()` saves page HTML/screenshot/traceback to `/tmp/openoutreach-diagnostics/`.
- **`core/scheduler.py`** — Single owner of Task row creation. Window planners (`plan_connect_window` / `plan_follow_up_window` / `plan_check_pending_window`) emit lazy slots with `1 immediate + (n-1) Poisson-spaced`; `poisson_slot_times(now, n, horizon_hours)` + `working_seconds_in_window(start, end)` are the spacing primitives. `flush_email_queue(session, campaign)` is the eager-drain counterpart for email — immediate, un-spaced slots for the READY_TO_EMAIL pool, capped by `Mailbox.objects.remaining_today()`. State-transition hook `on_deal_state_entered` only stamps `Deal.next_check_pending_at` for PENDING. `reconcile()` recovers stale RUNNING + runs the window planners and the email flush per campaign.
- **`linkedin/tasks/connect.py`** — `handle_connect`, `ConnectStrategy`.
- **`linkedin/tasks/check_pending.py`** — `handle_check_pending`, exponential backoff.
- **`linkedin/tasks/follow_up.py`** — `handle_follow_up`, rate limiting.
- **`linkedin/pipeline/qualify.py`** — `run_qualification()`, `fetch_qualification_candidates()`.
- **`linkedin/pipeline/search.py`** — `run_search()`, keyword management.
- **`linkedin/pipeline/search_keywords.py`** — `generate_search_keywords()` via LLM.
- **`linkedin/pipeline/ready_pool.py`** — GP confidence gate, `promote_to_ready()`.
- **`linkedin/pipeline/pools.py`** — Composable generators: `search_source` → `qualify_source` → `ready_source`.
- **`linkedin/pipeline/freemium_pool.py`** — Seed priority + undiscovered pool, ranked by qualifier.
- **`linkedin/ml/qualifier.py`** — `Qualifier` protocol, `BayesianQualifier`, `KitQualifier`, `qualify_with_llm()`.
- **`linkedin/ml/embeddings.py`** — FastEmbed utilities, `embed_text()`, `embed_texts()`.
- **`linkedin/ml/profile_text.py`** — `build_profile_text()`.
- **`linkedin/ml/hub.py`** — HuggingFace kit loader (`fetch_kit()`).
- **`linkedin/browser/session.py`** — `AccountSession` (a `linkedin_cli.session.LinkedInSession`): linkedin_profile, page, context, browser, playwright. `campaigns` cached_property (list, via Campaign.users M2M). `ensure_browser()` launches/recovers browser via `linkedin.browser.launch.start_browser_session`. `self_profile` cached_property — scrapes via the `linkedin_cli` self-discovery primitive on first access (no DB cache; one extra scrape per daemon restart) and persists the disqualified self-lead via `db.leads.register_self_lead`. Cookie expiry check via `_maybe_refresh_cookies()`. `reauthenticate()` forces fresh login.
- **`linkedin/browser/registry.py`** — `get_or_create_session()`, `get_first_active_profile()`, `resolve_profile()`, `cli_parser()`/`cli_session()` (Django bootstrap for `follow_up.py`'s `__main__`).
- **`linkedin/browser/launch.py`** — `start_browser_session()` + `_save_cookies()`: the daemon's launch/persistence orchestration — launch the stealthed browser (via `linkedin_cli.browser.login.launch_browser`), restore/persist cookies to the Django DB, run the login flow (`linkedin_cli.auth.authenticate`), validate a saved session. The reusable browser/login *mechanics* live in `linkedin_cli`; this is the Django/DB glue.
- **`linkedin/db/leads.py`** — Lead CRUD, `get_leads_for_qualification()`, `disqualify_lead()`, `_cache_urn_from_profile()`, `register_self_lead()` (persists the logged-in member as a disqualified self-lead on top of the `linkedin_cli` self-discovery primitive).
- **`core/db/deals.py`** — Deal/state ops, `set_profile_state()` (also fires `_capture_contact_info()` on the CONNECTED transition), `increment_connect_attempts()`, `create_freemium_deal()`.
- **`linkedin/db/chat.py`** — `sync_conversation()`, `_sync_from_api()`, folds newly-synced messages into `Deal.chat_summary` via `update_chat_summary`.
- **`signals/analysis_service.py`** — V1 Anansi Atlas analysis orchestration. Builds analyzer input from Organization/Project rows, stores `OrganizationAnalysisRun`, updates analyzer-owned Organization/Project fields, and upserts one `FundingCriteria` row.
- **`signals/analyzer.py`** — Deterministic, local analyzer used by V1 and tests. Produces organization summary, service/focus/beneficiary/capability extraction, warnings, search keywords, program summaries, and funding criteria without network or LLM calls.
- **`signals/views.py`** — Authenticated intake, analysis review, run-analysis POST, Executive Dashboard, Mission Brief, FundingSignal dashboard, GovernmentSignal dashboard, ResourceSignal dashboard, PartnershipSignal dashboard, Opportunity Matching dashboard, Discovery Engine dashboard, Opportunity Pipeline workspace, lifecycle transition POST, owner assignment POST, EcosystemSignal dashboard, and remaining module placeholder views. GovernmentSignal V1 is deterministic public-sector lane planning only; ResourceSignal V1 is deterministic non-funding resource readiness only; PartnershipSignal V1 is deterministic partnership readiness and targeting only; Opportunity Matching V3 is deterministic weighted local opportunity database matching plus strategic improvement analysis only; Discovery Engine V2 is a deterministic manually managed opportunity management layer only; Opportunity Lifecycle V1/V2 is deterministic lifecycle grouping, stage guidance, stage transitions, owner assignment, and pipeline health only; EcosystemSignal V1 is deterministic cross-signal opportunity ecosystem readiness only; live opportunity discovery, government/resource/partner search, web crawling, procurement scraping, monitoring automation, agents, embeddings, vector search, AI scoring, real grant matching automation, real partner matching automation, and external databases remain intentionally out of scope.
- **`signals/dashboard.py`** — Deterministic Anansi Atlas Executive Dashboard V1 helper. It composes Mission Brief analysis metadata, FundingSignal, GovernmentSignal, ResourceSignal, PartnershipSignal, EcosystemSignal, Discovery, Opportunity Matching, Lifecycle, and Celebrations into a compact command-center context: executive header metrics, KPI scorecards, opportunity web counts, pipeline columns, lifecycle summary counts, match health, discovery health, top leverage actions, latest Wins Across the Web, and chart-ready distribution data. It performs no AI, crawling, APIs, agents, embeddings, vector search, live discovery, or fake trend generation.
- **Anansi Atlas Brand Update V1 + Celebration Area V1** — User-facing brand/content update only. The app shell, dashboard, intake, module templates, demo command output, docs, and visible copy use Anansi Atlas, The Web of Opportunity, `anansiatlas.com`, and Scott Foundry Group LLC operator language while preserving Django app labels, Python packages, model names, database tables, and routes. The dashboard Celebration Area deterministically highlights recent wins, milestones, and progress from existing opportunities, lifecycle state, tasks, deadlines, documents, evidence, and readiness data without notifications or real-time feeds.
- **Celebrations V1 / Wins Across the Web V1 / Global Footer Cleanup V1** — Adds `Celebration` records for project-scoped mission progress, `/projects/<id>/celebrations/`, dashboard latest-celebration widget, deterministic demo celebration examples, and a shared subtle footer with the Threaded A text mark, Anansi Atlas, The Web of Opportunity, `anansiatlas.com`, and Scott Foundry Group LLC operator text. The sidebar navigation now exposes Dashboard, Organization, Opportunities, Ecosystem, Readiness, Documents, Evidence, Celebrations, and Workspace Settings. No scoring, matching, discovery, or readiness logic changes.
- **Anansi Atlas App Shell V1** (`signals/templates/signals/_app_shell_sidebar.html`, `_app_shell_styles.html`) — Shared premium SaaS layout applied across the Executive Dashboard, Mission Brief, FundingSignal, GovernmentSignal, ResourceSignal, PartnershipSignal, Discovery, Opportunity Matching, and EcosystemSignal. It provides the common left sidebar, active-page navigation, card rhythm, spacing, and typography layer without changing backend scoring, matching, discovery, or access-control logic.
- **Anansi Atlas UX V2** — Workflow-oriented presentation layer. The primary shell navigation is Dashboard, Organization, Opportunities, Ecosystem, and Settings; `project_organization_workspace.html` groups Mission Brief, profile, programs, outcomes, and readiness data; `project_opportunities_workspace.html` groups Discovery, Matching, and Pipeline so users can think in terms of opportunities instead of internal modules. Existing module routes remain available as tabs/detail views.
- **Anansi Atlas UI Polish V1** — UI-only refinement of the shared app shell, Executive Dashboard, Discovery table, pipeline cards, chart-ready containers, workspace tabs, and status/priority visual indicators. It improves executive scanning, card consistency, CRM-style opportunity readability, responsive table overflow, and the prominent "What To Do Next" advisor panel without changing routes, scoring, matching, discovery, database models, or calculations.
- **Anansi Atlas UI Polish V2** — UI-only refinement of premium visual density and usability across Dashboard, Organization, Opportunities, Discovery, Matching, Ecosystem, and Settings. It standardizes badge treatments for status/priority/match/readiness states, strengthens empty and low-data states, upgrades CRM-style table presentation, makes advisor actions numbered with impact labels, improves card hover/active navigation states, and prioritizes executive scanning without changing routes, scoring, matching, discovery, database models, or calculations.
- **Anansi Atlas UI Cleanup V3 + Opportunity Category Expansion** — Presentation and deterministic taxonomy refinement. Dashboard, Discovery, Matching, Ecosystem, and Opportunities use progressive disclosure for longer secondary sections; Discovery adds compact filter affordances, top/more category display, and focus-category breakdowns from existing opportunity JSON fields. The shared category vocabulary expands supported focus areas across veterans, homelessness, healthcare, mental health, LGBTQ+, disability, food security, housing, reentry/justice-involved, youth, workforce, digital equity, education, small business, arts/culture, community development, senior services, immigrant/refugee support, environmental justice, and rural communities. Inventory matching can use the expanded vocabulary, while core opportunity database matching remains deterministic and stable. No live search, APIs, crawling, agents, external databases, or schema changes are introduced.
- **Anansi Atlas UI Cleanup V4** — Opportunities workspace presentation cleanup. The first scan emphasizes opportunity health, high-priority opportunities, active opportunities, and upcoming deadlines; total counts and secondary match details move behind disclosure. Top opportunities and opportunity categories are collapsible, show compact top slices first, and provide "View All Opportunities", "Show More", "More Categories", "Show All Categories", and "Collapse Categories" affordances without changing scoring, matching, discovery, models, or routes.
- **Anansi Atlas UI Cleanup V5** — EcosystemSignal presentation cleanup. The first scan emphasizes ecosystem score, strongest signal, weakest signal, highest-leverage action, and opportunity health; match/discovery health and deeper ecosystem details move behind disclosure. Funder types, government entity types, resource types, resource categories, and partnership categories render as compact collapsible summaries with top slices, "More..." sections, Show All, and Collapse affordances using existing readiness outputs only.
- **Anansi Atlas UI Polish V3** — Uniformity pass across shared shell and signal module templates. The shared style layer standardizes score boxes, card rhythm, collapsible summaries, spacing, section toolbars, checklist rows, and advisor/action list styling. FundingSignal, GovernmentSignal, ResourceSignal, and PartnershipSignal use the same page pattern as the newer workspaces: eyebrow/title/subtitle, score card, recommended next actions, compact summary cards, primary content, and secondary details behind disclosure. No scoring, matching, discovery, model, route, or permission behavior changes.
- **Anansi Atlas UX V4** — Command-center presentation pass. Discovery inventory rows show summary-only opportunity, status, priority, deadline, and match score columns by default, with source organization, match reasons, missing factors, improvement opportunities, focus areas, beneficiaries, eligibility notes, internal notes, and recommended actions behind expandable row details. Matching cards show decision-level fields first, including score, potential score, confidence, and primary recommendation, while detailed factors stay behind collapsible sections. No scoring, matching, discovery, model, route, or permission behavior changes.
- **Opportunity Lifecycle V1 / Pipeline V2 / Lifecycle Actions V2 / Opportunity Workspace V1** — Deterministic opportunity management layer over the manually managed Opportunity inventory. `/projects/<id>/pipeline/` groups opportunities by lifecycle stage and Pipeline V2 renders Salesforce/HubSpot-style operating columns with compact scored opportunity cards, source/type/priority/deadline/owner/next-step fields, stage-specific action prompts, compact transition buttons, owner assignment controls, and expandable detail panels for notes, eligibility, focus areas, beneficiaries, match reasons, missing factors, improvement opportunities, and status-history placeholders. Lifecycle Actions V2 supports the deterministic stage path from Discovered through Closed, preserves notes, appends status-history entries, and updates `updated_at`; Owner Assignment V1 supports assign-to-me/unassign using the existing `assigned_owner` field. Opportunity Workspace V1 adds `/projects/<project_id>/opportunities/<opportunity_id>/` as the pursuit work hub with Overview, Requirements, Tasks, Deadlines, Notes, and History sections. `OpportunityTask` and `OpportunityDeadline` store manually managed work items and deadline tracking; `signals/opportunity_work.py` creates stage-specific default tasks and submission/internal-review deadlines idempotently, computes task/deadline health, and feeds Dashboard, Pipeline, Discovery, Matching, and workspace summaries. Discovery and Pipeline link directly into workspaces, Matching exposes top inventory workspaces, and Dashboard shows Opportunity Work Summary. It does not add drag-and-drop, collaboration, AI, agents, crawling, APIs, external databases, or live discovery.
- **Readiness Engine V1 / Organization Completeness V1 / Opportunity Pursuit Readiness V1** — Deterministic readiness layer over existing Anansi Atlas data only. `/projects/<id>/readiness/` shows overall readiness, organization completeness, completed/missing areas, highest-leverage missing area, readiness dimensions, strengths, gaps, actions, and opportunity pursuit readiness summary. `signals/readiness.py` computes organization completeness from Mission Brief/Profile fields plus existing signal readiness scores; overall readiness from mission/program/outcome/funding/government/partnership/resource/operational dimensions; and per-opportunity pursuit readiness from completeness, document/task readiness, outcomes, budget, capacity, partnerships, resources, and deadline health. Dashboard shows Organization Completeness, Readiness Score, Top Readiness Gap, and Top Readiness Action; EcosystemSignal shows Readiness Health; Opportunity Workspace shows pursuit readiness and missing areas; Pipeline/Discovery show compact readiness badges; Matching shows pursuit readiness and combined opportunity health. It performs no AI, agents, crawling, APIs, external databases, live discovery, or schema changes.
- **Score Transparency V1** — Deterministic explanation layer for major Anansi Atlas scores. `signals/score_transparency.py` turns existing readiness, organization completeness, pursuit readiness, match overview, forecast, and relationship health outputs into reusable explanation objects with score contributors, score gaps, and highest-leverage actions. Dashboard, Readiness, Matching, Pipeline, Ecosystem, Relationship, and Opportunity Workspace templates render these explanations compactly or behind disclosure. It does not change scoring, matching, forecasting, relationship logic, routes, models, permissions, or data collection.
- **Opportunity Web Visualization V1** — Deterministic visual foundation for The Web of Opportunity. `/projects/<id>/web/` renders a card/pathway ecosystem from Mission to Funders, Partners, Contacts, Resources, Opportunities, and Outcomes using existing organization profile data, relationship tracking, document/evidence health, Discovery, and forecast outputs. Dashboard shows an Opportunity Web Summary and Ecosystem links into the page. It adds no AI, agents, graph database, D3, force-directed visualization, APIs, external databases, models, or external data collection.
- **Public Landing Page V1 / Email Capture V1 / Pilot Onboarding V1 / Opportunity Web Snapshot V1** — Public-facing Anansi Atlas entry point and local pilot capture layer. `/anansi-atlas/` renders the public landing page, stores `InterestSignup` submissions locally, and sends a best-effort plain-text Django email notification to `info@anansiatlas.com`; signup persistence is not rolled back if email delivery fails. `/anansi-atlas/thanks/` confirms receipt; `/pilot/` explains the Founding Atlas Partners onboarding focus areas; `/projects/<id>/snapshot/` renders a member-only executive Opportunity Web Snapshot from existing Opportunity Web, readiness, funding, partnership, Discovery, document/evidence, and matching outputs. Dashboard and Opportunity Web link to the Snapshot. It adds no paid email providers, newsletter platforms, Stripe, AI, agents, crawlers, APIs, external databases, or CRM/email/calendar integrations.
- **Anansi Atlas Hosting Notes / Production Prep V1** — `docs/anansi_atlas_hosting.md` records the observed `anansiatlas.com` DNS state, production Django/email variables, recommended deployment target, current-host questions, and live-site requirements. `docs/anansi_atlas_deployment_checklist.md` provides the go-live checklist. Settings remain local-first but support environment-driven `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, Django email settings, and optional PostgreSQL `DATABASE_URL`; no DNS, deployment, or secret changes are performed by the app.
- **Document Vault V1 / Evidence Library V1 / Opportunity Document Requirements V1** — Deterministic document and evidence management layer. `/projects/<id>/documents/` summarizes `DocumentVaultItem` records by readiness score, status, type, missing critical documents, and available/missing/update counts. `/projects/<id>/evidence/` summarizes `EvidenceLibraryItem` records by readiness score, status, type, outcome evidence, impact stories, and missing evidence. `OpportunityDocumentRequirement` tracks opportunity-specific required documents/evidence, links to vault items when present, and is created idempotently by deterministic opportunity-type suggestions. Opportunity Workspace includes Documents and Evidence sections; Dashboard shows Document/Evidence Summary; Pipeline/Discovery/Matching show compact document/evidence/submission readiness context; Readiness Engine includes Document, Evidence, and Submission readiness dimensions. Demo seed creates at least eight documents, eight evidence items, and requirements for demo opportunities with available/missing/needs-update examples. It performs no AI, agents, crawling, APIs, external databases, live discovery, or automated parsing.
- **`signals/government.py`** — Deterministic GovernmentSignal V1 helper. It reads Project, Organization, and optional FundingCriteria rows to produce a government opportunity readiness score, public-sector lanes, scored government entity recommendations, engagement checklist rows, and gap-specific government actions. It performs no network calls.
- **`signals/ecosystem.py`** — Deterministic EcosystemSignal V1 helper. It combines Mission Brief profile completeness, FundingSignal readiness, GovernmentSignal readiness, ResourceSignal readiness, PartnershipSignal readiness, and the Opportunity Matching summary into an opportunity ecosystem score, signal scorecards, aggregated strengths/gaps, priority opportunity areas, recommended ecosystem actions, and ecosystem summary categories. It performs no network calls.
- **`signals/discovery.py`** — Deterministic Discovery Engine V2 helper. It reads manually managed `Opportunity` inventory records and their `SourceOrganization` owners, groups them as grants/government/resources/partnerships and by high/medium/low priority, reuses Opportunity Matching scoring for readiness signals, and summarizes totals, active/upcoming/monitoring/applied/won counts, source organizations, status breakdown, geography coverage, lifecycle summary, and Discovery Health for EcosystemSignal. It performs no search, crawling, APIs, agents, automated ingestion, AI discovery, embeddings, vector search, or external database access.
- **`signals/lifecycle.py`** — Deterministic Opportunity Lifecycle V1/Pipeline V2 helper. It defines lifecycle stage order, allowed transitions, stage descriptions, stage-specific recommended next steps/action prompts, active/qualified/submitted/awarded/stale/overdue lifecycle health counts, 0-100 Pipeline Health scoring with Excellent/Healthy/Needs Attention/At Risk levels, highest-priority active opportunity selection, owner assignment helpers, status-history updates, and grouped board columns for the pipeline workspace. It reads and updates local `Opportunity` rows only and performs no automation or external calls.
- **`signals/opportunity_work.py`** — Deterministic Opportunity Workspace V1 helper. It defines lifecycle-stage task templates, creates default tasks and deadline records idempotently, computes task totals/open/complete/blocked/overdue counts, computes upcoming/due-soon/overdue/completed deadline health, builds lightweight requirements, and supplies workspace/dashboard/pipeline/discovery summaries. It reads and writes only local `Opportunity`, `OpportunityTask`, and `OpportunityDeadline` rows.
- **`signals/readiness.py`** — Deterministic Readiness Engine V1 helper. It computes organization completeness, overall readiness dimensions, recommended readiness actions, opportunity pursuit readiness, and pursuit summary averages from local Project/Organization, existing signal readiness outputs, Opportunity, OpportunityTask, and OpportunityDeadline rows only.
- **`signals/score_transparency.py`** — Deterministic Score Transparency V1 helper. It formats existing score outputs into contributor/gap/highest-leverage-action explanations for readiness, organization completeness, pursuit readiness, matching, forecasting, and relationship health without recalculating or changing the underlying scores.
- **`signals/opportunity_web.py`** — Deterministic Opportunity Web Visualization V1 helper. It builds node summaries, opportunity gaps, and highest-leverage actions from local Project/Organization, relationship, document/evidence, Discovery, and forecast data only.
- **`signals/snapshot.py`** — Deterministic Opportunity Web Snapshot helper. It formats existing Opportunity Web, readiness, funding, partnership, Discovery, document/evidence, and matching outputs into a lightweight executive report with top pathways, resource gaps, risks/gaps, top opportunities, and next actions.
- **`signals/documents.py`** — Deterministic Document Vault/Evidence Library helper. It computes document readiness, evidence readiness, opportunity document/evidence requirements, submission readiness impact, missing critical documents, missing evidence, and opportunities blocked by missing documents from local `DocumentVaultItem`, `EvidenceLibraryItem`, `OpportunityDocumentRequirement`, and `Opportunity` rows only.
- **`signals/matching.py`** — Deterministic Opportunity Matching V3 helper. It reads only local Project/Organization/FundingCriteria profile data and active Opportunity Database records (`Funder`, `GovernmentEntity`, `ResourceProvider`, `PartnerOrganization`) to produce weighted 0-100 scores, confidence levels, current/potential scores, match factor breakdowns, missing profile factors, improvement opportunities, top gap analysis, category heatmap, highest-leverage actions, readiness signals, and ranked recommendations. It performs no AI scoring, embeddings, vector search, network calls, crawling, or external database access.
- **`signals/resources.py`** — Deterministic ResourceSignal V1 helper. It reads Project, Organization, and optional FundingCriteria rows to produce a resource readiness score, strengths/gaps, non-funding resource categories, scored resource recommendations, checklist rows, actions, and ecosystem snapshot. It performs no network calls.
- **`signals/partnerships.py`** — Deterministic PartnershipSignal V1 helper. It reads Project, Organization, and optional FundingCriteria rows to produce a partnership readiness score, strengths/gaps, partner categories, scored partner recommendations, checklist rows, actions, and ecosystem snapshot. It performs no network calls.
- **`signals/demo.py`** and **`signals/management/commands/seed_missionsignal_demo.py`** — Idempotent local demo seeding for a demo user, organization, Primary Initiative project, deterministic analysis, BridgeForward-style Opportunity Database examples across funders, government entities, resource providers, partner organizations, source organizations, at least 20 manually managed Discovery Engine opportunity inventory records with varied statuses, priorities, geographies, categories, and match scores, plus deterministic document vault, evidence library, and opportunity requirement records.
- **`funding/management/commands/import_opportunities_csv.py`** — Admin-oriented deterministic CSV import for manually managed opportunity inventory rows. Required columns are `name`, `opportunity_type`, `geography`, and `status`; optional columns include source organization, deadline, notes, focus areas, beneficiaries, and priority. It performs no external discovery or API access.
- **`funding/identity.py`** and **`funding/services.py`** — Canonical URL normalization, stable opportunity identity-key construction, and source-record-to-opportunity resolution.
- **`funding/readiness.py`** — Deterministic FundingSignal V2 helper used by the dashboard. It reads Project, Organization, and optional FundingCriteria rows and performs no network calls.
- **`sources/hashing.py`** — Stable filter hashing for source query uniqueness.
- **`core/db/summaries.py`** — Single mem0-style LLM boundary. `materialize_profile_summary_if_missing(deal, session)` fires on first follow-up touch (one Voyager re-scrape per `(lead, campaign)` lifetime); `update_chat_summary(deal, new_messages, *, seller_name)` folds newly-synced ChatMessages incrementally via `reconcile_facts`, which routes new facts through mem0's UPDATE prompt to apply ADD/UPDATE/DELETE/NONE events (mirrors `mem0/memory/main.py::Memory._add_to_vector_store` lines 594-700, with vector-store ops replaced by an in-memory dict because `Deal.chat_summary` is a flat list). `_format_messages_for_extraction` filters to incoming messages only, so `chat_summary` holds facts about the lead and a one-sided outgoing burst is a noop. `extract_facts(text, *, seller_name, context)` runs `pydantic_ai.Agent(get_llm_model(), output_type=FactList)` against the vendored `_FACT_EXTRACTION_PROMPT` plus an unconditional identity-binding block (`_build_identity_binding`) telling the LLM that `[Me]` is `seller_name`, so seller-name greetings in `[Lead]` messages don't get misattributed to the lead. `reconcile_facts(existing, new, *, seller_name)` prepends the same binding to mem0's UPDATE prompt with an explicit "DELETE contamination" instruction — previously-stored facts that describe the seller as the lead *should* clean up on the next sync that produces a conflicting fact, though this is best-effort (the upstream mem0 prompt is example-heavy and the cleanup hint is one prepended sentence; dormant deals stay contaminated). `seller_name_from(session)` is the single derivation point — `first_name` from `session.self_profile` with username fallback. mem0's `DEFAULT_UPDATE_MEMORY_PROMPT` and `get_update_memory_messages` live under `openoutreach/core/vendor/mem0/configs/prompts.py` (mirrors upstream path so future syncs are a clean diff; pinned commit recorded in the file header).
- **`core/conf.py`** — Config constants, `CAMPAIGN_CONFIG`. LLM construction lives in `llm.py`. (Browser/Voyager/fixture constants moved to `linkedin_cli/conf.py`.)
- **`core/llm.py`** — `get_llm_model()` factory + `run_agent_sync(coro)` sync boundary. `get_llm_model()` reads `SiteConfig` and dispatches via per-provider builders (OpenAI / Anthropic / Google / Groq / Mistral / Cohere / openai_compatible) to the right `pydantic_ai.models.Model`. Call sites build `Agent(get_llm_model(), ...)` and invoke `run_agent_sync(agent.run(prompt))` — never `Agent.run_sync`, whose anyio portal leaves the caller's thread running-loop slot populated and poisons subsequent sync Playwright calls (`"using Playwright Sync API inside the asyncio loop"`). `run_agent_sync` drives the coroutine to completion on a short-lived worker thread with its own event loop; per-thread asyncio slots are independent, so the caller's thread stays clean regardless of what anyio / pytest-anyio / Jupyter / etc. did to it.
- **`core/onboarding.py`** — Interactive setup.
- **`core/agents/follow_up.py`** — Follow-up agent. Single LLM call with structured output (`FollowUpDecision`). Conversation is read in Python and injected into the prompt. No tool-calling loop.
- **`linkedin/api/newsletter.py`** — `subscribe_to_newsletter()` via Brevo form, `ensure_newsletter_subscription()`. No config parsing — subscribe_newsletter is a BooleanField. (The LinkedIn-platform `api/` — `client`, `voyager`, `messaging/` — moved to `linkedin_cli`.)
- **`linkedin/setup/freemium.py`** — `import_freemium_campaign()`, `seed_profiles()`.
- **`linkedin/setup/geo.py`** — country-code jurisdiction lines: `is_gdpr_protected()`/`apply_gdpr_newsletter_override()` (broad email-opt-in set, drives newsletter) and `is_eea_located()`/`EEA_UK_CH` (narrow EEA/UK/CH collection-regime set, gates contacts-store contribution + forced give-back).
- **`linkedin/setup/seeds.py`** — User-provided seed profiles: parse URLs, create Leads + QUALIFIED Deals.
- **`core/management/setup_crm.py`** — Idempotent CRM bootstrap (Site creation).
- **`admin.py`** (per app) — Django Admin: `core/admin.py` (SiteConfig, Campaign, Task), `linkedin/admin.py` (LinkedInProfile, SearchKeyword, ActionLog), `chat/admin.py` (ChatMessage).
- **`settings.py`** — Django settings (SQLite at `data/db.sqlite3`). Apps: crm, chat, core, linkedin, emails, signals, sources, funding.


## `linkedin_cli` — Standalone LinkedIn Library (Django-free)

External package ([`eracle/linkedin-cli`](https://github.com/eracle/linkedin-cli),
installed via the `requirements/base.txt` git dependency) holding the LinkedIn
*platform mechanics* (browser nav, login form, Voyager API, profile/conversation
scrape, the connect/message/status/thread verbs), so the daemon and external
agents share one surface. Imports with **no Django** configured and holds no DB.
The module docs below describe the installed package's surface.

**Transport — bind + connect.** A session *owner* launches a browser and
`browser.bind()`s it (Playwright ≥1.59); clients attach via `chromium.connect()`
with a real `Page`, and `playwright-cli attach <name>` can share the same browser
(e.g. for a human to clear a checkpoint). The daemon owns its browser in-process;
the standalone CLI's `session open` launcher owns it for non-daemon use.

- **`session.py`** — `LinkedInSession` Protocol (the contract verbs run against:
  `page`, `context`, `self_profile`, `ensure_browser()`, `wait()`, `close()`).
  `PlaywrightCliSession` connects to a bound browser (`chromium.connect(endpoint)`).
  Session registry (`write_session`/`read_session`/`clear_session`,
  `linkedin_cli_home()`) maps a session name → bound-browser websocket endpoint.
- **`launcher.py`** — `open_bound_session()`: launch a persistent browser,
  `bind()` it, register the endpoint, block. The standalone session owner.
- **`cli.py`** — verb CLI over bind+connect (`python -m linkedin_cli.cli`):
  `session open/close`, `login`, `whoami`, `search`, `profile`, `status`, `connect`,
  `message`, `thread`. **Output contract** (documented in the module docstring so
  it travels with the package): every verb produces a result dict; the default is
  a brief human-readable summary on stdout, and `--json` (on every verb) emits the
  full dict — redirect with `>` to save it (no `--out`; clig.dev composability).
  stdout carries only the result; logs and errors go to stderr as
  `error: <type>: <message>` + non-zero exit (`type` mirrors `exceptions.py`).
  Owns interaction-pacing policy (injected into the session).
- **`page_state.py`** — the page-state machine. `classify_page(page)` judges the
  live page by **URL path only** (a `/login?session_redirect=…/feed/` redirect must
  not read as the feed). `@transition(when=, then=)` is a contract decorator over an
  action: it enforces the precondition state *and*, re-reading the page after the
  action, that the result is in the allowed `then` set — raising `IllegalPageTransition`
  otherwise (the postcondition is what a held-state FSM can't express). `PageFlow` is
  the generic engine: `.transition` registers an action under its `when`; `.run()` is
  the single observe→act loop that drives a session to the flow's goal.
- **`auth.py`** — the auth flow, declared as `@auth_flow.transition` actions
  (unknown/authwall/login/checkpoint → feed); no hand-written loop. `authenticate(session,
  *, username=, password=)` stamps credentials and runs the flow to the feed. Shared by
  the CLI `login` verb and the daemon (`openoutreach/linkedin/browser/launch.py`), so both drive one
  enforced login path. Rejected credentials = landing back on `/login`, which the
  `_from_login` contract forbids → surfaces as `AuthenticationError` (and enforces
  never-resubmit).
- **`linkedin/browser/login.py`** — login form mechanics: locators,
  `submit_login_form(session, username, password)` (fills + submits, asserts nothing —
  the auth flow re-reads the page), `dismiss_comply_gate()`, `await_checkpoint_clear()`,
  `launch_browser()`.
- **`linkedin/browser/nav.py`** — `goto_page()`, `human_type()`, `find_top_card()`, `dump_page_html()`.
- **`actions/`** — `connect.py` (`send_connection_request`), `status.py`
  (`get_connection_status`), `message.py` (`send_raw_message`), `profile.py`
  (`scrape_profile`), `search.py` (`search_people` — returns a
  `{query, page, network, profiles:[{public_identifier, url}]}` envelope, optional
  `network` degree filter; backs the `search` verb and is used in-process by the
  daemon — plus `visit_profile`), `conversations.py` (`get_conversation`).
- **`api/client.py`** — `PlaywrightLinkedinAPI`: in-page `fetch()` for authentic
  headers; `get_profile()` with tenacity retry; `VOYAGER_REQUEST_TIMEOUT_MS`.
- **`api/voyager.py`** — `LinkedInProfile` parse (`parse_linkedin_voyager_response()`,
  `parse_connection_degree()`).
- **`api/messaging/`** — `send.py` (`send_message`), `conversations.py`
  (`fetch_conversations`/`fetch_messages`), `utils.py` (`encode_urn`/`check_response`).
- **`linkedin/setup/self_profile.py`** — `discover_self_profile(session)`: Voyager `me`
  scrape → dict, no persistence (the disqualified-lead write is OpenOutreach's
  `db.leads.register_self_lead`).
- **`core/conf.py`** — browser/timeout/fixture constants (`BROWSER_*`, `HUMAN_TYPE_*`,
  `BROWSER_HEADLESS`, `CHECKPOINT_RESOLVE_TIMEOUT_S`, fixture dirs).
  **`exceptions.py`** (`AuthenticationError`, `SkipProfile`,
  `ProfileInaccessibleError`, `ReachedConnectionLimit`, `CheckpointChallengeError`),
  **`enums.py`** (`ProfileState` — the library's internal enum for the 3 UI-observed
  states its connect/status verbs detect; the CRM funnel is OpenOutreach's `DealState`,
  see Profile State Machine), **`url_utils.py`** (`url_to_public_id`/`public_id_to_url`).


## Configuration

- **`SiteConfig`** (DB singleton) — `llm_provider` (required, defaults to `openai`; choices: `openai`/`anthropic`/`google`/`groq`/`mistral`/`cohere`/`openai_compatible`), `llm_api_key` (required), `ai_model` (required), `llm_api_base` (required only for `openai_compatible`), `finder_api_key` (optional — BetterContact email-finder key; blank disables enrichment). Editable via Django Admin.
- **`conf.py` schedule** — `ENABLE_ACTIVE_HOURS` (`False`), `ACTIVE_START_HOUR` (9), `ACTIVE_END_HOUR` (19), `ACTIVE_TIMEZONE` (system-local IANA name, falls back to "UTC"). Daemon sleeps outside this window. No weekend/rest-day handling — humans use LinkedIn 7 days a week.
- **`conf.py` planner cap** — `CHECK_PENDING_DAILY_CAP` (100). Maximum `check_pending` slots planned per 24h window per campaign; overflow rolls into the next planning cycle.
- **`conf.py:CAMPAIGN_CONFIG`** — `min_ready_to_connect_prob` (0.9), `min_positive_pool_prob` (0.20), `check_pending_recheck_after_hours` (24), `qualification_n_mc_samples` (100), `enrich_min_delay_seconds` (6), `enrich_max_delay_seconds` (10), `enrich_max_per_page` (10), `burst_min_seconds` (2700), `burst_max_seconds` (3900), `break_min_seconds` (600), `break_max_seconds` (1200), `min_action_interval` (120), `embedding_model` ("BAAI/bge-small-en-v1.5").
- **Prompt templates** (at `openoutreach/core/templates/prompts/`) — `qualify_lead.j2` (temp 0.7), `search_keywords.j2` (temp 0.9), `follow_up_agent.j2`.
- **`requirements/`** — `base.txt`, `local.txt`, `production.txt`, `crm.txt` (empty — DjangoCRM installed via `--no-deps`).

## Docker

Base image: `mcr.microsoft.com/playwright/python:v1.55.0-noble`. VNC on port 5900. `BUILD_ENV` arg selects requirements. Dockerfile at `compose/linkedin/Dockerfile`. Install: uv pip → DjangoCRM `--no-deps` → requirements → Playwright chromium.

## CI/CD

- `tests.yml` — pytest in Docker on push to `master` and PRs.
- `deploy.yml` — Tests → build + push to `ghcr.io/eracle/openoutreach`. Tags: `latest`, `sha-<commit>`, semver.

## Dependencies

`requirements/` files. DjangoCRM's `mysqlclient` excluded via `--no-deps`. `uv pip install` for fast installs.

Core: `playwright`, `playwright-stealth`, `Django`, `django-crm-admin`, `pandas`, `pydantic-ai-slim` (with `openai`/`anthropic`/`google`/`groq`/`mistral`/`cohere`/`bedrock` extras), `jinja2`, `pydantic`, `jsonpath-ng`, `tendo`, `termcolor`, `tenacity`
ML: `scikit-learn`, `numpy`, `fastembed`, `joblib`
