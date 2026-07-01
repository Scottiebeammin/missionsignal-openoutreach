# Anansi Ads — n8n automation (same system as Myths & Midnight)

This reuses the **existing n8n pipeline** (Docker on the Intel Mac) that already runs the Myths & Midnight flow (Schedule → ElevenLabs → MP3). `anansi-ads.n8n.json` is an importable workflow that does the same for the Anansi ads, then renders the final MP4.

## The flow (mirrors Myths, + a render step)
```
Daily 6am  →  Due ads today  →  List ElevenLabs Voices  →  Pick voice id  →  ElevenLabs TTS  →  Save MP3  →  Render MP4 (Remotion)
(schedule)   (filter by date)   (auto-pull by name)        (name → id)       (audio)            (public/)     (out/<id>.mp4)
```
- **Auto-pulls the voice by name** — same ElevenLabs account/credential you use for Joey Patel on Myths; here it resolves Christopher / Jackson / Siren / Giselle.
- **Date-driven** — each ad has a `scheduledDate` (from the July calendar: Showcase **Jul 8**, Pilot **Jul 16**). Only ads due *today* build.
- The first six nodes are identical in spirit to the Myths pipeline; the last node adds the video assembly Myths hasn't built yet.

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
This n8n workflow and the Node scripts (`scripts/generate-vo.mjs`, `scripts/build-scheduled.mjs`) do the same job two ways — use whichever fits: **n8n** for the always-on scheduled pipeline (like Myths), the **Node scripts** for manual/local runs. Both auto-pull the voice by name and read the same ad definitions.
