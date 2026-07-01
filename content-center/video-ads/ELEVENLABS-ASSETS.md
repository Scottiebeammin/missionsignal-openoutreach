# ElevenLabs → Remotion asset workflow

*Created: 2026-07-01 · Anansi Atlas Content Center*

You have voice + **Veo video** + music in your ElevenLabs subscription. Here's how each drops into our Remotion videos. The pattern is always: **you generate in ElevenLabs → export → drop the file in the right folder → tell me the filename → I wire it into the composition and render.**

## 1. Voice (already wired ✅)
- Scripts live in `ads.config.mjs`. Run `npm run vo` (or `npm run vo <id>`) — it auto-pulls the voice by name and writes `public/*.mp3`.
- Studio plays it with sound (audio is set in the composition's `defaultProps`).

## 2. B-roll video (ElevenLabs Veo)
For cinematic shots our screen-recordings can't do — a nonprofit leader at a laptop, hands typing, a quiet office, abstract light/network motion.
1. Generate the clip in ElevenLabs (Video). **Export as MP4.**
2. Save it to **`public/broll/`** (e.g. `public/broll/leader-laptop.mp4`).
3. Tell me the filename + where you want it (cold-open, a section cutaway, the transformation beat).
4. I composite it with the **`BRoll`** component — it plays full-frame under a navy→gold overlay so it matches the brand and any text on top stays readable.

**⚠️ Prompt tip (important):** the typing clip you generated shows **"www.anansia.com"** on the screen — Veo hallucinated a domain (our real one is `anansiatlas.com`). **Don't let Veo render readable text/logos/UI** — it makes up wrong words. Prompt for *abstract or human* footage instead:
- ✅ "close-up of hands typing on a backlit keyboard, dark room, shallow depth of field, no screen text, cinematic, warm key light"
- ✅ "a focused nonprofit director at a laptop in a bright community office, over-the-shoulder, blurred background, warm, documentary"
- ❌ anything showing a website, dashboard, or words on a monitor (that's what our real `ScreenshotPanel` shots are for — the product UI must always be the *real* thing).

Recommended B-roll clips to generate (for the walkthrough cold-open + cutaways):
1. Hands typing / laptop, dark, no screen text — the "scattered work" open.
2. Nonprofit leader looking thoughtfully at a laptop, bright office — the human stakes.
3. Abstract gold light threads / particles on dark — brand connective tissue.

## 3. Music
- Generate a soft cinematic bed in ElevenLabs (Music) — calm pulse + minimal percussion, ~90s, no big drops. Export MP3.
- Save to `public/music/` (e.g. `public/music/bed.mp3`); tell me and I add it as a **second low-volume audio track** (`<Audio volume={0.12}>`) under the VO.

## The build-together loop
1. **You:** generate assets in ElevenLabs (voice ✅ / B-roll / music), export, drop in `public/broll` or `public/music`.
2. **You:** tell me the filenames + intent.
3. **Me:** wire them into the composition (Claude Code), re-render.
4. **You:** review live in **Remotion Studio (localhost:3000)** — plays with sound, scrub the timeline.
5. Iterate.

> Generated media (`public/broll/*`, `public/music/*`, `public/*.mp3`) is gitignored — the source code + this workflow are what's version-controlled, so anyone can regenerate.
