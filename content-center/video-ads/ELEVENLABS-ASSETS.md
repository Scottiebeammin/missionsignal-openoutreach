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

### Exactly what to generate for ProductWalkthrough (3 clips, wired and waiting)
The composition already has the slots open — drop these in `public/broll/` with these **exact filenames** and it just works, no code changes needed:

#### `hands-typing.mp4` → cold-open, `broll1Src` (6.0s exactly — the composition's cold-open is timed to this shot)
**LOCKED SPEC** (this is the canonical prompt — cinematic, 4-beat storyboard, continuous dolly). Generate as a single unbroken 6-second clip, do not cut a second clip into it:

> Use the provided 4-frame storyboard sheet as the direct sequential visual keyframe reference for the entire 6-second video. Follow the exact 4-beat progression and pacing.
>
> **THE SUBJECT:** Adult hands typing on a backlit mechanical keyboard. Natural adult skin tone, no rings or jewelry, relaxed natural typing posture. Fingers move fluidly across keys. Same hands throughout — identical skin tone, posture, and keyboard.
>
> **THE SETTING:** Dark room, near-total darkness beyond the desk surface. No screens visible. No monitors. No UI. No text on any surface. Desk surface barely visible in shadow. Same environment throughout — NO bright frames, NO overhead light.
>
> **THE LIGHTING:** Warm amber-golden key light raking from camera-left, creating rim separation on fingers and knuckles. Chiaroscuro. Crushed blacks. No fill light. Keyboard backlight provides subtle upward glow on palms. Same lighting throughout.
>
> **CONSTRAINTS:** Do not reorder or skip beats. No extra characters or props. No text overlays, no logos, no watermarks, no UI, no screens visible anywhere.
>
> **SHOT SEQUENCE — 4 beats, ~1.5s each, 6 seconds total:**
> [0:00–0:02] ESTABLISH — Medium close-up. Both hands resting lightly on keyboard, fingers poised above keys. Keyboard fills lower two-thirds of frame. Warm amber rim light catches knuckle edges. Deep black background. Camera begins slow dolly-in.
> [0:02–0:03] PUSH BEGINS — Medium close-up tightening. Fingers begin to move, slight motion blur on tips. Key backlight glows between gaps. Dolly continuing steadily.
> [0:03–0:05] KEY DETAIL — Close-up. Three or four keys fill frame, fingertips pressing down, shallow depth of field, keys sharp, background bokeh. Amber rim light wraps around fingertips.
> [0:05–0:06] EXTREME CLOSE — Extreme close-up. Single finger pressing one key, key fully depressed, backlight blooming softly around fingertip. Maximum bokeh. Warm golden glow. Cinematic stillness.
>
> **SOUND:** Quiet dark room ambience throughout. Subtle mechanical key clicks — soft tactile thud with each keystroke. No music. No voices.
> **CAMERA:** Slow continuous dolly-in from medium close-up to extreme close-up over 6 seconds. Smooth, no shake.
> **STYLE:** Photorealistic cinematic, ARRI Alexa look, warm amber-orange color grade, crushed blacks, chiaroscuro, shallow depth of field throughout, mechanical keyboard backlight glow. NO screens, NO UI, NO text on any surface.

Export at **6.0 seconds** — the composition's cold-open (`BROLL_LEAD`) is set to exactly 180 frames (6s) to match this shot's full 4-beat progression. If Veo can't hit exactly 6.0s, tell me the actual length and I'll adjust `BROLL_LEAD` to match (one constant in `ProductWalkthrough.tsx`). Our brand text ("The Web of Opportunity") is added by us afterward as an overlay — it is NOT part of the generated clip.

#### `problem.mp4` → Act 1 "the problem" background, `problemBrollSrc`
> overhead shot of a cluttered desk — sticky notes, an open laptop with blank dark screen, coffee cup, papers, someone's hands sorting through them, muted natural light, documentary style, no readable text anywhere

#### `laptop-office.mp4` (or `.jpg` — a still photo works fine) → Act 2 "website reveal," `officeEnvSrc`
A real screenshot composites onto this laptop's screen.
> a modern laptop open on a wooden desk in a bright, minimal nonprofit office, camera facing the laptop straight-on and slightly above, screen angled toward camera, completely blank matte dark screen, soft window light, shallow depth of field, no text, no logos, photorealistic, static shot

**Once you drop these 3 files in**, tell me "broll is in" — I'll set them in `Root.tsx` and re-render. For `laptop-office`, the screenshot gets composited into a percentage-based screen region that assumes a roughly front-facing, flat laptop (per the prompt above) — if it looks off after the first render, tell me and I'll nudge the `screenRect` coordinates in `LaptopFrame` (in `src/components.tsx`) to match your exact shot.

### Other recommended clips (for the other flagship videos, later)
- Nonprofit leader looking thoughtfully at a laptop, bright office — the human stakes (PremiumShowcase/FullExplainer).
- Abstract glowing gold light threads on dark navy — brand connective tissue, usable as a transition/cutaway anywhere.

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
