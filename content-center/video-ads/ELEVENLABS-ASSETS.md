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

### Exactly what to generate for ProductWalkthrough (4 clips, wired and waiting)
The composition already has the slots open — drop these in `public/broll/` with these **exact filenames** and it just works, no code changes needed:

| Filename | Used for | Prompt (paste as-is) |
|---|---|---|
| `hands-typing.mp4` | cold-open (first half, `broll1Src`) | `close-up of hands typing on a backlit keyboard, dark room, shallow depth of field, no text or UI visible on any screen, cinematic, warm key light` |
| `gold-threads.mp4` | cold-open (second half, `broll2Src`) | `abstract glowing gold light threads connecting on a dark navy background, slow motion, elegant, no text` |
| `problem.mp4` | Act 1 "the problem" background, under the headline text (`problemBrollSrc`) | `overhead shot of a cluttered desk — sticky notes, an open laptop with blank dark screen, coffee cup, papers, someone's hands sorting through them, muted natural light, documentary style, no readable text anywhere` |
| `laptop-office.mp4` (or `.jpg` — a still photo works fine too) | Act 2 "website reveal" — a real screenshot composites onto this laptop's screen (`officeEnvSrc`) | `a modern laptop open on a wooden desk in a bright, minimal nonprofit office, camera facing the laptop straight-on and slightly above, screen angled toward camera, completely blank matte dark screen, soft window light, shallow depth of field, no text, no logos, photorealistic, static shot` |

**Once you drop these 4 files in**, tell me "broll is in" — I'll set them in `Root.tsx` and re-render. For `laptop-office`, the screenshot gets composited into a percentage-based screen region that assumes a roughly front-facing, flat laptop (per the prompt above) — if it looks off after the first render, tell me and I'll nudge the `screenRect` coordinates in `LaptopFrame` (in `src/components.tsx`) to match your exact shot.

### Other recommended clips (for the other flagship videos, later)
5. Nonprofit leader looking thoughtfully at a laptop, bright office — the human stakes (PremiumShowcase/FullExplainer).

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
