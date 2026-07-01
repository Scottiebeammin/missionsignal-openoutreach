# Anansi Atlas — LinkedIn Ad Commercials (Remotion)

*Created: 2026-07-01 · Anansi Atlas Content Center (Scott Foundry Group LLC)*

Two production-ready **30-second, 1:1 square** ad commercials built as code with [Remotion](https://remotion.dev) — they render to real MP4s for LinkedIn. Add-on; touches no app code.

| Composition | Purpose | Assigned VO voice |
|---|---|---|
| **PlatformShowcase** | "Who we are / what we do" product showcase → apply for the pilot | **Christopher** |
| **PilotSignup** | Drive Founding Atlas Partners Pilot applications (scarcity: 19 seats) | **Jackson** |

Both are navy/charcoal/gold, Fraunces + Inter, and recreate the real product UI (orb-web hero, Snapshot bubble cards, "What To Do Next"). Snapshot is shown as **included in the paid pilot** — never "free."

## Prerequisites (already on this machine)
Node, npm, ffmpeg, and Chrome are installed. First time only:
```bash
cd content-center/video-ads
npm install
```

## Preview / edit
```bash
npm start          # opens Remotion Studio in the browser — scrub, tweak, preview live
```

## Render to MP4
```bash
npm run render:showcase   # -> out/platform-showcase.mp4
npm run render:pilot      # -> out/pilot-signup.mp4
npm run render:all
```
Renders are silent by default (no VO). See below to add narration.

## Subtitles
Both ads have a **baked-in bottom caption bar** synced to the VO (defined as `CAPTIONS` in each ad file). LinkedIn autoplays muted, so viewers read the message even with sound off. Edit the caption text/timing in `src/ads/*.tsx`; keep it matching the VO script in `ads.config.mjs`.

## Adding the voiceover — two ways

### Option A — Manual (no API key)
1. In ElevenLabs, generate each script (see `ads.config.mjs`) with its assigned voice. Export MP3.
2. Save as `public/showcase-vo.mp3` (Christopher) and `public/pilot-vo.mp3` (Jackson).
3. Render with audio: `npm run build`  (auto-detects the VO files and wires them in).

### Option B — Automated (ElevenLabs API — recommended)
The pipeline **auto-pulls the voice by name** from your ElevenLabs account (no voice IDs to manage) and generates the MP3s for you.
```bash
export ELEVENLABS_API_KEY=sk_...     # your key — NEVER commit it (see security note)
npm run vo                            # generates public/*.mp3 for every ad (auto-resolves Christopher/Jackson/…)
npm run build                         # renders both MP4s with VO + subtitles
```
`npm run vo PilotSignup` does just one ad. Voice names, scripts, and settings all live in `ads.config.mjs`.

> **Security:** the ElevenLabs key is a secret. Keep it in your shell env (or a local `.env` you never commit — `.env` is gitignored). Don't paste it into any tracked file. I can't enter or store the key for you — you set it yourself.

## Automation — auto-generate on the dates in your calendar
The July calendar (`../07-content-calendar-july-2026.md`) now has a **"Voice Needed" column** on every dated post — at a glance, whoever's producing that day's content knows exactly which ElevenLabs voice (if any) the clip needs. `ads.config.mjs` is the machine-readable mirror of that column: every entry carries a `scheduledDate`, the `voice`, and either a `script` to generate or a `reuseAudioFrom` pointer (for re-cuts that reuse an earlier day's narration, like the Jul 11 repurpose of the Jul 8 walkthrough).

Two kinds of entries:
- **`kind: "remotion"`** (PlatformShowcase, PilotSignup) — a full ad composition exists; the scheduler generates the VO **and** renders the final MP4.
- **`kind: "voiceover-only"`** (Jul 10, 17, 24, 25, 31) — no Remotion composition yet for that day's talking-head/b-roll clip; the scheduler still **auto-generates the narration MP3** (voice auto-pulled by name) so it's ready to drop into whatever tool cuts that day's video. Build a Remotion comp later to fully automate the video too.

`scripts/build-scheduled.mjs` builds/generates whatever's **due today**:
```bash
ADS_DATE=2026-07-08 npm run build:scheduled     # dry-run a specific date
ADS_DATE=2026-07-10 npm run build:scheduled     # voiceover-only example
ADS_DATE=2026-07-11 npm run build:scheduled     # reuse example — no API key needed if the source VO already exists
npm run build:scheduled                          # builds whatever's due TODAY
```
Run it automatically once a day with **cron** (machine must be on, key available) — same pattern as the n8n pipeline in `automation/`:
```bash
# crontab -e  — every day at 6am, build/generate anything due that day
0 6 * * * cd /Users/scottiebeammin/Documents/GitHub/missionsignal-openoutreach/content-center/video-ads && ELEVENLABS_API_KEY=sk_... /usr/local/bin/node scripts/build-scheduled.mjs >> out/scheduled.log 2>&1
```
Or import `automation/anansi-ads.n8n.json` into the same n8n instance that runs the Myths & Midnight pipeline — it does the identical schedule→auto-pull-voice→TTS flow (see `automation/README.md`).

To schedule a **new** dated post: add an entry to both the calendar's Voice Needed column *and* `ADS` in `ads.config.mjs` (`voice`, `script` or `reuseAudioFrom`, `audioOut`, `scheduledDate`, `kind`) — the scheduler picks it up on that date. (For a fully hands-off server pipeline, this same script can run in any CI/cron with Node + ffmpeg + Chrome.)

**Timing note:** both timelines are 30s (900 frames @ 30fps). If your VO runs longer/shorter, either trim the read or adjust `durationInFrames` in `src/Root.tsx` and the `<Sequence>` offsets in the ad file. Check your VO length: `ffprobe -i public/showcase-vo.mp3 -show_entries format=duration -v quiet -of csv="p=0"`.

## VO SCRIPTS (paste into ElevenLabs)

### PlatformShowcase — voice: Christopher (~30s)
> Your next opportunity is already out there.
> It's just scattered — across funder portals, emails, spreadsheets, and relationships.
> Anansi Atlas maps the web of opportunity around your mission: funders, partners, government pathways, resources, and readiness.
> Your Opportunity Web Snapshot shows your strongest asset, your biggest gap, and the single highest-leverage move to make next.
> Anansi Atlas. Apply for a founding seat at anansi atlas dot com, slash anansi atlas.

### PilotSignup — voice: Jackson (~30s)
> Applications are open for the Founding Atlas Partners Pilot.
> We're selecting nineteen nonprofit and mission-driven organizations.
> Each partner receives a guided Opportunity Web Snapshot, a forty-five minute walkthrough, and the living platform.
> A hundred and fifty dollars a month, locked for life, for the first twenty organizations.
> Nineteen seats remain. Apply now at anansi atlas dot com, slash anansi atlas.

## LinkedIn upload specs
- Format: MP4 (H.264) — what these render as. ✅
- Aspect: 1:1 (1080×1080) — renders here; strong in the LinkedIn feed. ✅
- Length: 30s (LinkedIn allows up to 10 min; 15–30s is ideal for feed ads). ✅
- **Captions:** LinkedIn autoplays muted — most viewers won't hear the VO. Consider baking on-screen captions (the ads already carry key on-screen text; for full spoken-word captions, add a caption track in `src/` or upload an .srt on LinkedIn).

## Files
- `src/brand.ts` — brand tokens (kept in sync with `00-brand-brief.md`)
- `src/components.tsx` — shared brand components (NavyBG, OrbWeb, BubbleCard, CTA…)
- `src/ads/PlatformShowcase.tsx` · `src/ads/PilotSignup.tsx` — the two ads
- `src/Root.tsx` — composition registry
