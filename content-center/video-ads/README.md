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

## Add the ElevenLabs voiceover
1. In ElevenLabs, generate each script below with its assigned voice (warm, credible, calm-confident — see brand brief). Export as MP3.
2. Save them here:
   - `public/showcase-vo.mp3`  (Christopher)
   - `public/pilot-vo.mp3`     (Jackson)
3. Render **with** audio by passing the prop:
```bash
npx remotion render PlatformShowcase out/platform-showcase.mp4 --props='{"audioSrc":"showcase-vo.mp3"}'
npx remotion render PilotSignup      out/pilot-signup.mp4      --props='{"audioSrc":"pilot-vo.mp3"}'
```
(Or set `audioSrc` in `src/Root.tsx` defaultProps, or in Studio's props panel.)

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
