# Anansi Ads — n8n automation (same system as Myths & Midnight)

This reuses the **existing n8n pipeline** (Docker on the Intel Mac) that already runs the Myths & Midnight flow (Schedule → ElevenLabs → MP3). `anansi-ads.n8n.json` is an importable workflow that does the same for the Anansi ads, then renders the final MP4.

## The flow (mirrors Myths, + a render step)
```
Daily 6am  →  Due ads today  →  List ElevenLabs Voices  →  Pick voice id  →  ElevenLabs TTS  →  Save MP3  →  Render MP4 (Remotion)
(schedule)   (filter by date)   (auto-pull by name)        (name → id)       (audio)            (public/)     (out/<id>.mp4)
```
- **Auto-pulls the voice by name** — same ElevenLabs account/credential you use for Joey Patel on Myths; here it resolves Christopher / Jackson / Siren / Giselle.
- **Date-driven** — each ad has a `scheduledDate` (from the July calendar's **Voice Needed** column: Showcase **Jul 8**, Pilot **Jul 18**). Only ads due *today* build.
- The first six nodes are identical in spirit to the Myths pipeline; the last node adds the video assembly Myths hasn't built yet.

**Scope note:** this n8n workflow currently automates the **two full Remotion ads** (PlatformShowcase, PilotSignup). The July calendar has 8 more dated posts that need a voice pulled but have no Remotion composition yet (Jul 3/4/10/11/17/24/25/31 — see the calendar's Voice Needed column). Those are already covered by the **Node scheduler** (`scripts/build-scheduled.mjs` in the parent folder, run via cron or by hand) — it auto-generates just the narration MP3 for those days, ready to drop into whatever tool cuts that day's talking-head/b-roll clip. Extend this n8n workflow's `ADS` array the same way once you want those on the n8n side too.

## One-time setup
1. **Import:** n8n → Workflows → Import from File → `anansi-ads.n8n.json`.
2. **ElevenLabs credential:** create an n8n **Header Auth** credential named **`ElevenLabs API`** — header name `xi-api-key`, value = your ElevenLabs key (the same key/account as Myths). Assign it to both HTTP nodes. *(The key lives in n8n's credential store — never in this JSON or the repo.)*
3. **Path env:** set `ANANSI_ADS_DIR` (n8n env / container env) to this `video-ads` folder path, mounted into the container — e.g. `/data/anansi/video-ads`. `Save MP3` writes to `$ANANSI_ADS_DIR/public/…` and the render runs there.
4. **Activate** the workflow. Test now with `ADS_DATE_OVERRIDE=2026-07-08` set in the n8n env to force that day's build.

## The render step (Execute Command) — same caveat as Myths' video assembly
`Render MP4 (Remotion)` runs `node scripts/build.mjs <id>`, which needs **Node + ffmpeg + headless Chrome** available where the command runs. Two options:
- **If your n8n container has them** (or you add them to the image): it renders end-to-end inside n8n.
- **If not** (typical — Myths keeps video assembly outside n8n): **delete/disable that last node**. n8n then does exactly what Myths does (schedule → VO → MP3 saved to `public/`), and you run the render on the host with `npm run build` (which auto-detects the fresh MP3s). Same split Myths already uses.

## Adding a new scheduled ad
Edit the `ADS` array in the **Due ads today** node (and keep `ads.config.mjs` in sync for the host-side scripts): add `{ id, voice, audioOut, scheduledDate, text }`. The workflow picks it up on that date.

## Relationship to the host scripts
This n8n workflow and the Node scripts (`scripts/generate-vo.mjs`, `scripts/build-scheduled.mjs`) do the same job two ways — use whichever fits: **n8n** for the always-on scheduled pipeline (like Myths), the **Node scripts** for manual/local runs. Both auto-pull the voice by name; the Node side reads `ads.config.mjs` (the full month, including voiceover-only posts), while this n8n workflow currently mirrors just the two full-video entries from it.

---

# Anansi Outreach — n8n workflow (`anansi-outreach.n8n.json`)

The **sales side** of the same n8n instance: every weekday at 8am it reads the canonical
lead CSV, picks the next **15 hottest un-contacted leads** (warm wins over cold, hot > warm >
reconnect), composes personalized drafts (warm = shared-memory opening; cold = Florida
founder opening), and emails Marcus **one approval digest**. Marcus approves/tweaks → sends →
marks `email_status` in the CSV. Any reply = stop automation, go human.

## The lead-feed contract (from the vault)
- **Canonical CSV:** `scott-obsidian-vault/08_Assets/anansi-atlas-pipeline-system.csv` — one row
  per lead, stable headers. Full schema on the **Schema (n8n)** tab of
  `anansi-atlas-sales-pipeline-MASTER.xlsx` (lead_id, dedup_key, is_warm, …).
- **Reconcile rules:** upsert on normalized email (`dedup_key`), **warm wins**, never downgrade,
  refresh non-empty fields, bump `last_updated`. Reference implementation:
  `08_Assets/reconcile_pipeline.py` (dependency-free Python); the Code node carries a JS twin
  (`reconcileRows()`) for wiring an ingest branch later.

## One-time setup
1. Import `anansi-outreach.n8n.json` (n8n → Workflows → Import from File).
2. Mount the vault's `08_Assets` into the container and set env **`OUTREACH_DIR`** to it.
3. Set env: **`WALKTHROUGH_VIDEO_URL`** (unlisted YouTube walkthrough — the hero CTA in every
   email), `STRIPE_MONTHLY_URL`, `STRIPE_ANNUAL_URL`, `CAL_URL`, optional `BATCH_SIZE` (15).
4. Assign your SMTP credential (same mail account as the platform) to the digest node.
5. Activate. The digest lands at info@anansiatlas.com each weekday morning.

## July 2026 rendered assets (`out/july-2026/`)
All July calendar assets are pre-rendered (no n8n render step needed): dated folders
(`jul-08-platform-walkthrough/` … `jul-31-closing-outro/`), `jul-02-carousel/` slides,
`thumbnails/`, and **`youtube/` = the upload queue** (YouTube-ready renders, e.g.
`Jul08-PlatformWalkthrough-YouTube.mp4` — upload unlisted, then its link becomes
`WALKTHROUGH_VIDEO_URL` above and fills the `[VIDEO LINK]` placeholder across the
email library / day files in the vault).
