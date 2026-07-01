# Anansi Atlas — Ad Creation Brand & Motion System

*Created: 2026-07-01 · Anansi Atlas Content Center (Scott Foundry Group LLC)*

**This is the established template for every Anansi Atlas video ad.** When we build any new ad from the content calendar, it uses this system — so the brand looks and sounds like one company across every post. Nothing here is decided per-ad; it's decided once, here.

> Source of truth for *messaging* = `../00-brand-brief.md`. This doc is the *video/motion* system that sits on top of it.

---

## 0. Production tiers (decided 2026-07-01)
Not every ad gets the same budget of time. Two tiers, on purpose:

**🌟 FLAGSHIP — pin these, invest deeply.** Custom B-roll, laptop-in-office compositing, cinematic VO, longer runtime. These are the evergreen "hero" assets (website, pinned post, outreach, YouTube) — worth polishing until they're genuinely great.
- `oneoffs/ProductWalkthrough.tsx` — the full journey, B-roll cold-open + laptop compositing
- `oneoffs/PremiumShowcase.tsx` — the ~85s brand commercial
- `oneoffs/FullExplainer.tsx` — the 5-min deep walkthrough

**⚡ LIGHTER PRODUCTIONS — fast, template-only, no custom B-roll.** These are the day-to-day July-calendar posts. Build them straight from `_TEMPLATE.tsx` and the existing component library (`ScreenshotPanel`, `BubbleCard`, `CTAButton`…) — real product screenshots, no bespoke shoots. Quick to produce, still on-brand, no bottleneck waiting on B-roll generation.
- `ads/PlatformShowcase.tsx`, `ads/PilotSignup.tsx`, and every dated `Jul##-*.tsx` clip

**Rule of thumb:** if it needs a new B-roll clip or laptop compositing, it's flagship-tier — budget the time. If it's built from existing screenshots + components, it's a lighter production — knock it out fast. Revisit this list as budget/time opens up; a lighter production can always graduate to flagship treatment later.

---

## 0b. The build workflow — every new video, every time (added 2026-07-01)
**Skeleton → Timing → Motion → Polish.** Don't jump straight to polish — build in this order:

1. **Basic skeleton** — get every beat/scene on screen with placeholder timing (round numbers). Confirm the *structure* and *story* are right before touching motion. Render a **still frame** at a few key points (`npx remotion still <id> out/check.png --frame=N`) to sanity-check layout/colors — don't wait on a full render to catch a layout bug.
2. **Add timing** — derive real durations from the actual VO (word-count-proportional split — see `scripts/generate-vo.mjs` output + the retiming math in `ProductWalkthrough.tsx`/`PremiumShowcase.tsx` for the pattern). Get the cuts landing on the right words before touching motion polish.
3. **Refine motion** — apply the Pro-Prompts rules (§0c below): full enter *and* exit on everything, stagger multi-element reveals, anticipation/overshoot/settle instead of linear/robotic motion, subtle idle life on anything holding on screen.
4. **Polish** — sound design (whoosh/click/chime/swish, trimmed silence, balanced levels), one tasteful animated accent (border light-travel, shine sweep — good use for `LottieAsset`), payoff moment on the key CTA/number.

**Once a workflow produces a good result, save it as a template** for next time — either extend `_TEMPLATE.tsx` or add a named preset/snippet here. Don't rebuild a pattern from scratch twice.

## 0c. Motion polish rules (adapted from the Rangy AI "Motion-Graphics Starter Kit," 2026-07-01)
- **The #1 rule: every element animates in AND fully out before the clip ends.** Nothing pops in abruptly or gets cut off mid-motion. Audit every `<Sequence>` boundary against this.
- Avoid robotic linear motion — anticipation (tiny wind-up) → slight overshoot → settle. Use `spring()` or GSAP's `back`/`elastic` eases (see §0d).
- Stagger multi-element reveals (a few frames apart, not all at once) — `CheckLine`/`FeatureCard` lists already do this via `delay`; keep doing it on anything new.
- While something holds on screen, give it subtle life (gentle float, soft glow pulse, slow shine sweep) rather than a static freeze.
- Keep key text inside a ~10% title-safe margin; auto-fit/shrink long text rather than letting it overflow.
- Effects: prefer clean geometric light (flash, expanding ring, glow/bloom) over emoji/clip-art. One tasteful animated accent per scene, not clutter.
- Sound: soft whoosh on entrance, click/pop on key actions, chime on success, swish on exit — trim leading silence so hits land exactly on the beat, keep levels balanced.
- Workflow discipline: render a still at a key frame before the full clip; for a new flagship idea, sketch 2–3 style variations before polishing one.

## 0d. Animation library map — what to reach for, and when (added 2026-07-01)
Installed: `gsap`, `d3`, `three`, `@remotion/lottie` (already had it). Claude Code skills installed via `npx skills add` → `.agents/skills/` (gsap-core, gsap-timeline, gsap-plugins, gsap-utils, gsap-react, gsap-performance, gsap-frameworks, gsap-scrolltrigger, d3-viz, remotion-best-practices).

| Need | Reach for | Component |
|---|---|---|
| Basic fade/rise/scale, spring easing | Remotion's own `interpolate()` + `spring()` | `Rise`, `Headline`, `Eyebrow` — **default choice, covers 90% of cases** |
| Richer easing (back/elastic bounce, overshoot+settle) or multi-step sequencing with relative offsets (`"-=0.2"`) | **GSAP** (`gsap-core`, `gsap-timeline` skills) | `GsapRise` (new) |
| Kinetic typography (character/word-by-word reveal) | GSAP `SplitText` (`gsap-plugins` skill) | not yet wrapped — ask when needed |
| SVG line-draw (e.g. a cleaner `OrbWeb` thread-draw) | GSAP `DrawSVGPlugin` (`gsap-plugins` skill) | not yet wrapped — ask when needed |
| Pre-made polish accents (shine sweep, particle burst, checkmark pop) | **Lottie** JSON from LottieFiles → `public/lottie/` | `LottieAsset` (new) |
| Data-driven chart/stat visualization | **D3** (`d3-viz` skill) | not yet needed — no chart content today; use when we add a stat/chart video |
| 3D/WebGL | `three` | **parked** — doesn't fit our flat 2D brand look; only reach for it with a specific, deliberate 3D idea |
| Scroll-driven / drag interactions (ScrollTrigger, Draggable, Observer) | — | **not applicable** — we render headless video, not an interactive web page |

### ⚠️ The GSAP + Remotion rule — read this every time you reach for GSAP
GSAP has two fundamentally different modes. **Only one of them works in Remotion:**
1. **Live/ticker mode** (GSAP's default) — the animation runs on GSAP's own `requestAnimationFrame` ticker, tied to real wall-clock time. This is how GSAP works on a normal website. **Do not use this in Remotion** — Remotion renders frames out of real-time order (it can render frame 400 before frame 12), so a ticker-driven animation is non-deterministic and will render wrong/blank.
2. **Seek mode** (required in Remotion) — create the timeline with **`gsap.timeline({ paused: true })`**, then on every render call **`tl.time(frame / fps)`** or **`tl.progress(p)`** to set its state deterministically from Remotion's `useCurrentFrame()`. GSAP becomes a pure function of frame number, exactly like `interpolate()`/`spring()`.

`GsapRise` in `src/components.tsx` is the reference implementation — copy its pattern (`useEffect` builds the paused timeline once; `useLayoutEffect` seeks it every frame) for any new GSAP-powered component.

---

## 1. Brand essence (the one thing every ad must land)
- **Name / tagline:** Anansi Atlas — *The Web of Opportunity.*
- **Category:** nonprofit opportunity intelligence platform.
- **The single idea:** *The opportunity around your mission was never missing — it was scattered. We map it so you move from scattered opportunity to focused action.*
- **The offer, always:** Founding Atlas Partners Pilot · 20 seats · $150/mo locked for life · Snapshot + 45-min walkthrough included. **Never "free."**
- **Signup, always:** anansiatlas.com/anansi-atlas

## 2. Voice & tone (how every ad talks)
Clear · practical · strategic · warm · credible · direct · conversion-focused. Confident, not hype-y. We sound like a serious platform run by people who've been in the nonprofit seat — never a charity, never a startup shouting.

**Do:** short declarative sentences · "you/your" · concrete product nouns (Dashboard, Snapshot, Opportunity Web) · one idea per line.
**Don't:** guaranteed-funding claims · exaggerated AI hype · generic SaaS filler ("revolutionary synergy") · desperation · charity-pity framing · cartoon-spider / heavy folklore (tasteful weaver/web metaphor only).

## 3. Visual identity (locked — in `src/brand.ts`)
- **Colors:** navy `#0d1b3d` + charcoal `#101826` base · **gold `#d4a017`** accent · goldLight `#f3dd8c` · teal `#0f766e` = strength · gold = gap · rose `#c46a3d` = deadline/urgency.
- **Type:** **Fraunces** (serif) for headlines/wordmark · **Inter** for everything else. Eyebrows = Inter 800, uppercase, wide tracking, goldLight.
- **Formats:** 1:1 square (1080×1080) for LinkedIn feed · 9:16 vertical (1080×1920) for Reels/TikTok · 16:9 for YouTube (swap in `Root.tsx`).

## 4. Motion language (what makes it premium, not static)
Reusable components in `src/components.tsx` — **use these, don't reinvent:**
- **`AnimatedLogoReveal`** — gold threads converge → wordmark rises → shimmer sweep. The brand beat. Every hero/flagship ad opens or pivots on this.
- **`ScreenshotPanel`** — real product UI (`public/screenshots/*.png`) in a browser-chrome frame with cinematic Ken-Burns pan/zoom. **This is our signature move** — we always show the *real* website, never a fake mockup. Re-capture per `src/oneoffs/README.md`, always from the anonymized Creative Display profile (pk=1).
- **`OrbWeb`** — the six-node mission map assembling thread-by-thread. Our core visual metaphor.
- **`BubbleCard` / `FeatureCard` / `CheckLine`** — the card vocabulary (teal=strength, gold=gap).
- **`Subtitles`** — baked-in bottom captions on EVERY ad (LinkedIn/IG/TikTok autoplay muted).
- **`Rise` / `SectionMarker` / `ProgressRail`** — entrance motion + long-form orientation.
- **`SceneDissolve`** — a brief dip-to-navy between scenes for a smooth cross-dissolve. **Timing-safe** (an overlay, not a `TransitionSeries`), so it never desyncs the fixed-frame subtitles. Pass the scene-boundary frames.

**Pacing:** hero cuts ~4–7s per beat; feature reels ~12s per screen; nothing sits static — always a slow zoom, a rise, or a reveal in motion.

**Installed motion libraries** (available for richer effects on new ads): `@remotion/transitions` (TransitionSeries slide/wipe/fade — use on ads built fresh where you control timing + captions), `@remotion/media-utils` (VO-synced motion, audio waveforms), `@remotion/lottie` (drop-in Lottie micro-animations).

## 5. The standard ad structure (the 6-beat spine)
Every ad is some subset of these beats, in this order:
1. **Hook** (0–5s) — a sharp truth or question. Serif headline.
2. **Problem** (5–12s) — "scattered / lack of a system." Amber emphasis line.
3. **Brand reveal** — `AnimatedLogoReveal`. "This is Anansi Atlas."
4. **Product** — `ScreenshotPanel` of Dashboard → Opportunity Web → Snapshot (real UI in motion). The proof.
5. **Offer / belonging** — 20 seats, $150 locked for life, "join the family / founding partner."
6. **CTA** — logo lockup + gold pill button + signup URL. Verb: *Apply · Register Now · Join the Family.*

Short ads (8–30s) pick 2–3 beats; flagships (85s–5min) use all six with the product beat expanded.

## 6. Voice roster (ElevenLabs — auto-pulled by name)
Christopher (brand/walkthrough anchor) · Jackson (assertive CTA/offer) · Siren + Giselle (feature/variety). Warm, awake, credible read — never sleepy. Settings in `ads.config.mjs`.

---

## How to make a NEW ad (the repeatable workflow)
1. **Copy the starter:** duplicate `src/_TEMPLATE.tsx` → `src/ads/<YourAd>.tsx`, rename the component.
2. **Fill the 6 beats** — swap copy, pick which beats you need, point `ScreenshotPanel` at the right screenshot.
3. **Register it** in `src/Root.tsx` (id, duration, dimensions) and, if it's a dated calendar post, add it to `ads.config.mjs` (voice, script, scheduledDate).
4. **Preview live** in Remotion Studio (`npm start` → localhost:3000) — scrub, tweak timing.
5. **Add VO** — script goes in `ads.config.mjs` (or the oneoffs README); `npm run vo` auto-pulls the voice; re-render.
6. **Render:** `node scripts/build.mjs <id>` (or the scheduler for dated posts).

**Every ad checklist:** ✅ opens on-brand · ✅ shows real product (not a mockup) · ✅ subtitles on · ✅ one clear CTA to the signup link · ✅ "$150 locked for life," Snapshot never "free" · ✅ no guaranteed-funding / no cartoon spider · ✅ ends on the logo lockup.
